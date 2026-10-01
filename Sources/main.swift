import AppKit
import PDFKit
import UniformTypeIdentifiers
import ImageIO
import Darwin

struct ConvertError: LocalizedError {
 let message: String
 var errorDescription: String? { message }
}
func fail(_ s: String) -> ConvertError { ConvertError(message: s) }
final class ConversionJob {
 private let lock = NSLock()
 private var process: Process?
 private var cancelled = false
 func check() throws { lock.lock(); defer { lock.unlock() }; if cancelled { throw fail("변환을 취소했습니다.") } }
 func attach(_ value: Process) throws { lock.lock(); defer { lock.unlock() }; if cancelled { throw fail("변환을 취소했습니다.") }; process = value }
 func cancel() { lock.lock(); cancelled = true; let current = process; lock.unlock(); if let current, current.isRunning { current.terminate() } }
}
func convert(_ source: URL, job: ConversionJob = ConversionJob()) throws -> PDFDocument {
 try job.check()
 let attributes = try source.resourceValues(forKeys: [.isRegularFileKey,.isPackageKey,.fileSizeKey])
 guard attributes.isRegularFile == true || attributes.isPackage == true else { throw fail("일반 파일 또는 문서 패키지를 선택해 주세요.") }
 guard (attributes.fileSize ?? 0) <= 512 * 1024 * 1024 else { throw fail("512MB 이하의 파일을 선택해 주세요.") }
 let ext = source.pathExtension.lowercased()
 if ext == "pdf" {
  guard let doc = PDFDocument(url: source), !doc.isLocked else { throw fail("PDF를 읽을 수 없습니다. 암호화된 PDF는 먼저 잠금을 해제해 주세요.") }
  guard doc.allowsPrinting else { throw fail("인쇄가 허용되지 않은 PDF입니다.") }
  guard doc.pageCount > 0 && doc.pageCount <= 2000 else { throw fail("1~2000페이지 PDF를 선택해 주세요.") }
  return doc
 }
 if ["png","jpg","jpeg","tiff","tif","heic","bmp","gif"].contains(ext) {
  guard let imageSource = CGImageSourceCreateWithURL(source as CFURL,nil) else { throw fail("이미지를 읽을 수 없습니다.") }
  let count = ["tiff","tif"].contains(ext) ? CGImageSourceGetCount(imageSource) : 1
  guard count > 0 && count <= 2000 else { throw fail("이미지 페이지 수가 지원 범위를 벗어났습니다.") }
  let doc = PDFDocument()
  for i in 0..<count {
   try job.check()
   guard let image = CGImageSourceCreateImageAtIndex(imageSource,i,nil), image.width <= 20000, image.height <= 20000,
     let page = PDFPage(image: NSImage(cgImage:image,size:.zero)) else { throw fail("이미지 해상도 또는 형식을 지원하지 않습니다.") }
   doc.insert(page,at:doc.pageCount)
  }
  return doc
 }
 let office = ["doc","docx","docm","dot","dotx","rtf","odt","ott","ppt","pptx","pptm","pps","ppsx","odp","odg","xls","xlsx","xlsm","ods","csv","tsv","txt","html","htm","xhtml","epub"]
 let apple = ["pages":"pages", "key":"keynote", "numbers":"numbers"]
 let zipTypes = ["docx":"word/document.xml","docm":"word/document.xml","dotx":"word/document.xml","pptx":"ppt/presentation.xml","pptm":"ppt/presentation.xml","ppsx":"ppt/presentation.xml","xlsx":"xl/workbook.xml","xlsm":"xl/workbook.xml","hwpx":"Contents/","odt":"content.xml","ods":"content.xml","odp":"content.xml","odg":"content.xml","ott":"content.xml","epub":"META-INF/container.xml"]
 if let entry = zipTypes[ext] {
  let data = try Data(contentsOf:source,options:.mappedIfSafe)
  guard data.starts(with:[0x50,0x4b]), data.range(of:Data(entry.utf8)) != nil else { throw fail("문서 형식이 손상되었거나 암호화되어 있습니다.") }
  let archive = Process(); archive.executableURL = URL(fileURLWithPath:"/usr/bin/unzip"); archive.arguments = ["-Z","-t",source.path]
  var environment = ProcessInfo.processInfo.environment; environment["LC_ALL"] = "C"; archive.environment = environment
  let pipe = Pipe(); archive.standardOutput = pipe; archive.standardError = FileHandle.nullDevice
  try archive.run(); let summary = String(data:pipe.fileHandleForReading.readDataToEndOfFile(),encoding:.utf8) ?? ""; archive.waitUntilExit()
  let regex = try NSRegularExpression(pattern:"([0-9]+) bytes uncompressed")
  guard archive.terminationStatus == 0, let match = regex.firstMatch(in:summary,range:NSRange(summary.startIndex...,in:summary)), let range = Range(match.range(at:1),in:summary), let total = Int64(summary[range]), total <= 1024*1024*1024 else { throw fail("손상된 압축 문서이거나 압축 해제 크기가 1GB를 초과합니다.") }
 }

 guard office.contains(ext) || ["hwp","hwpx"].contains(ext) || apple[ext] != nil else { throw fail("지원하지 않는 형식입니다: .\(ext)\nOffice 문서, HWP/HWPX, 텍스트, HTML, PDF, 이미지 등을 선택해 주세요.") }
 let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("TopDF-\(UUID().uuidString)", isDirectory: true)
 try FileManager.default.createDirectory(at: tmp, withIntermediateDirectories: true)
 defer { try? FileManager.default.removeItem(at: tmp) }
 let input = tmp.appendingPathComponent(source.lastPathComponent)
 try FileManager.default.copyItem(at: source, to: input)
 // A Unicode BOM makes UTF-8 text independent of the user's OS locale.
 if ext == "txt" {
  let bytes = try Data(contentsOf: input)
  if String(data: bytes, encoding: .utf8) != nil && !bytes.starts(with: [0xef, 0xbb, 0xbf]) {
   try (Data([0xef, 0xbb, 0xbf]) + bytes).write(to: input)
  }
 }
 var output = tmp.appendingPathComponent("export.pdf")
 let process = Process()
 guard Bundle.main.resourceURL != nil else { throw fail("변환 엔진을 찾지 못했습니다.") }
 let helpers = Bundle.main.bundleURL.appendingPathComponent("Contents/Helpers")
 if ["hwp","hwpx"].contains(ext) {
  process.executableURL = helpers.appendingPathComponent("hwp")
  process.arguments = ["render",input.path,"--output",output.path,"--format","pdf","--font-dir","/System/Library/Fonts","--font-dir","/Library/Fonts","--font-dir",FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Fonts").path]
 } else if office.contains(ext) {
  process.executableURL = helpers.appendingPathComponent("LibreOffice.app/Contents/MacOS/soffice")
  let destination = tmp.appendingPathComponent("output", isDirectory: true)
  try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
  output = destination.appendingPathComponent(input.deletingPathExtension().lastPathComponent).appendingPathExtension("pdf")
  let profileUser = tmp.appendingPathComponent("profile/user",isDirectory:true)
  try FileManager.default.createDirectory(at:profileUser,withIntermediateDirectories:true)
  let settings = """
  <?xml version="1.0" encoding="UTF-8"?>
  <oor:items xmlns:oor="http://openoffice.org/2001/registry">
   <item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item>
   <item oor:path="/org.openoffice.Office.Calc/Content/Update"><prop oor:name="Link" oor:op="fuse"><value>0</value></prop></item>
   <item oor:path="/org.openoffice.Office.Writer/Content/Update"><prop oor:name="Link" oor:op="fuse"><value>0</value></prop></item>
  </oor:items>
  """
  try settings.write(to:profileUser.appendingPathComponent("registrymodifications.xcu"),atomically:true,encoding:.utf8)
  process.arguments = ["-env:UserInstallation=\(tmp.appendingPathComponent("profile").absoluteString)","--headless","--nologo","--nodefault","--nofirststartwizard","--convert-to","pdf","--outdir",destination.path,input.path]
 } else {
  guard let kind = apple[ext], let script = Bundle.main.url(forResource: kind, withExtension: "scpt") ?? Bundle.main.url(forResource: kind, withExtension: "applescript") else { throw fail("Apple 문서 변환 스크립트가 없습니다.") }
  process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript"); process.arguments = [script.path,input.path,output.path]
 }
 // Engine processes cannot make network connections. Apple apps are a separate, optional route.
 if apple[ext] == nil {
  guard let engine = process.executableURL else { throw fail("변환 엔진이 없습니다.") }
  let engineDirectory = helpers.path.replacingOccurrences(of:"\\",with:"\\\\").replacingOccurrences(of:"\"",with:"\\\"")
  let policy = "(version 1) (allow default) (deny network-outbound (remote ip \"*:*\")) (deny network-inbound (local ip \"*:*\")) (deny file-write* (subpath \"" + engineDirectory + "\"))"
  var environment = ProcessInfo.processInfo.environment; environment["PYTHONDONTWRITEBYTECODE"] = "1"; process.environment = environment
  process.arguments = ["-p",policy,engine.path] + (process.arguments ?? [])
  process.executableURL = URL(fileURLWithPath:"/usr/bin/sandbox-exec")
 }
 try job.attach(process)
 let pipe = Pipe(); process.standardError = pipe; process.standardOutput = FileHandle.nullDevice
 try process.run()
 let timeout = DispatchWorkItem {
  if process.isRunning { process.terminate(); DispatchQueue.global().asyncAfter(deadline:.now()+2) { if process.isRunning { kill(process.processIdentifier,SIGKILL) } } }
 }
 DispatchQueue.global().asyncAfter(deadline: .now() + 180, execute: timeout)
 let err = pipe.fileHandleForReading.readDataToEndOfFile(); process.waitUntilExit(); timeout.cancel(); try job.check()
 guard process.terminationStatus == 0 else { throw fail(String(data: err, encoding: .utf8) ?? "변환 엔진 실행 실패") }
 guard let doc = PDFDocument(url: output), doc.pageCount > 0, doc.pageCount <= 2000, let data = doc.dataRepresentation(), let loaded = PDFDocument(data: data) else { throw fail("문서 앱이 유효한 PDF를 만들지 못했습니다.") }
 return loaded
}

// Keep vector text and graphics when fitting a PDF page onto A4 paper.
func selectedPDF(_ doc: PDFDocument, first: Int, last: Int, layout: Int) throws -> PDFDocument {
 guard [0,1,2].contains(layout), first >= 1, last >= first, last <= doc.pageCount else { throw fail("페이지 범위를 1 ~ \(doc.pageCount) 안에서 입력해 주세요.") }
 let result = PDFDocument()
 for i in (first - 1)..<last {
  guard let p = doc.page(at: i) else { throw fail("페이지를 읽을 수 없습니다.") }
  if layout == 0 { result.insert(p.copy() as! PDFPage, at: result.pageCount); continue }
  var box = CGRect(x: 0, y: 0, width: layout == 1 ? 595.28 : 841.89, height: layout == 1 ? 841.89 : 595.28)
  let data = NSMutableData()
  guard let consumer = CGDataConsumer(data: data), let ctx = CGContext(consumer: consumer, mediaBox: &box, nil) else { throw fail("PDF 출력 생성 실패") }
  ctx.beginPDFPage(nil)
  ctx.setFillColor(NSColor.white.cgColor); ctx.fill(box)
  let bounds = p.bounds(for: .mediaBox)
  let rotated = p.rotation % 180 != 0
  let size = CGSize(width: rotated ? bounds.height : bounds.width, height: rotated ? bounds.width : bounds.height)
  guard size.width > 0, size.height > 0 else { throw fail("페이지 크기가 잘못되었습니다.") }
  let scale = min((box.width - 36) / size.width, (box.height - 36) / size.height)
  ctx.translateBy(x: (box.width - size.width * scale) / 2, y: (box.height - size.height * scale) / 2)
  ctx.scaleBy(x: scale, y: scale)
  guard let cgPage = p.pageRef else { throw fail("PDF 페이지를 읽을 수 없습니다.") }
  ctx.concatenate(cgPage.getDrawingTransform(.mediaBox,rect:CGRect(origin:.zero,size:size),rotate:0,preserveAspectRatio:true))
  ctx.drawPDFPage(cgPage)
  ctx.endPDFPage(); ctx.closePDF()
  guard let rendered = PDFDocument(data: data as Data)?.page(at: 0) else { throw fail("페이지 출력 실패") }
  result.insert(rendered, at: result.pageCount)
 }
 return result
}

func adjacentTarget(_ source: URL) -> URL {
 var target = source.deletingPathExtension().appendingPathExtension("pdf")
 var index = 1
 while FileManager.default.fileExists(atPath:target.path) {
  target = source.deletingLastPathComponent().appendingPathComponent("\(source.deletingPathExtension().lastPathComponent) (\(index)).pdf"); index += 1
 }
 return target
}
func writePDF(_ document: PDFDocument, to target: URL, replacing: Bool = false) throws {
 guard let data = document.dataRepresentation(), let verify = PDFDocument(data:data), verify.pageCount == document.pageCount else { throw fail("PDF 검증에 실패했습니다.") }
 if replacing { try data.write(to:target,options:.atomic); return }
 let staging = target.deletingLastPathComponent().appendingPathComponent(".TopDF-\(UUID().uuidString).pdf")
 defer { try? FileManager.default.removeItem(at:staging) }
 try data.write(to:staging,options:.atomic)
 let result = staging.path.withCString { from in target.path.withCString { to in renameatx_np(AT_FDCWD,from,AT_FDCWD,to,UInt32(RENAME_EXCL)) } }
 if result != 0 { throw NSError(domain:NSPOSIXErrorDomain,code:Int(errno),userInfo:[NSLocalizedDescriptionKey:"PDF를 저장하지 못했습니다. 같은 이름의 파일이 생겼거나 폴더에 쓰기 권한이 없습니다."]) }
}

final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
 var window: NSWindow!
 let preview = PDFView()
 let status = NSTextField(labelWithString: "파일을 선택하면 PDF 미리보기가 표시됩니다.")
 let layout = NSPopUpButton()
 let first = NSTextField(string: "1"), last = NSTextField(string: "1")
 let nearby = NSButton(checkboxWithTitle: "원본 파일 옆에 저장", target: nil, action: nil)
 var save: NSButton!, printButton: NSButton!
 var currentJob: ConversionJob?
 var doc: PDFDocument?, source: URL?, queue: [URL] = [], busy = false
 func applicationDidFinishLaunching(_ notification: Notification) {
  NSApp.servicesProvider = self; NSUpdateDynamicServices()
  buildUI()
  do { try installQuickAction() } catch { alert("우클릭 메뉴 설치 실패: " + error.localizedDescription) }
  if !queue.isEmpty { next() }
  else if CommandLine.arguments.count > 1 { enqueue(CommandLine.arguments.dropFirst().map { URL(fileURLWithPath: $0) }) }
  else { choose(nil) }
 }
 func buildUI() {
  window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 920, height: 700), styleMask: [.titled,.closable,.miniaturizable,.resizable], backing: .buffered, defer: false)
  window.title = "PDF로 변환"; window.minSize = NSSize(width: 880, height: 560); window.delegate = self; window.center()
  let root = NSStackView(); root.orientation = .vertical; root.spacing = 14; root.edgeInsets = NSEdgeInsets(top: 18, left: 20, bottom: 18, right: 20); root.translatesAutoresizingMaskIntoConstraints = false
  window.contentView!.addSubview(root)
  NSLayoutConstraint.activate([root.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor),root.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor),root.topAnchor.constraint(equalTo: window.contentView!.topAnchor),root.bottomAnchor.constraint(equalTo: window.contentView!.bottomAnchor)])
  let header = NSStackView(); header.orientation = .horizontal
  header.addArrangedSubview(NSButton(title:"도움말",target:self,action:#selector(help)))
  status.font = .systemFont(ofSize: 14, weight: .medium); status.lineBreakMode = .byTruncatingMiddle
  let chooseButton = NSButton(title: "파일 선택…", target: self, action: #selector(choose(_:)))
  header.addArrangedSubview(status); header.addArrangedSubview(chooseButton); root.addArrangedSubview(header)
  preview.autoScales = true; preview.displayMode = .singlePageContinuous; preview.backgroundColor = .controlBackgroundColor
  root.addArrangedSubview(preview)
  let options = NSStackView(); options.orientation = .horizontal; options.spacing = 10
  layout.addItems(withTitles: ["원본 크기·방향 유지", "A4 세로 · 페이지 맞춤", "A4 가로 · 페이지 맞춤"]); layout.target = self; layout.action = #selector(refresh)
  first.widthAnchor.constraint(equalToConstant: 55).isActive = true; last.widthAnchor.constraint(equalToConstant: 55).isActive = true
  for v in [NSTextField(labelWithString: "용지"),layout,NSTextField(labelWithString: "페이지"),first,NSTextField(labelWithString: "~"),last] as [NSView] { options.addArrangedSubview(v) }
  let apply = NSButton(title: "미리보기 적용", target: self, action: #selector(refresh)); options.addArrangedSubview(apply); root.addArrangedSubview(options)
  nearby.state = .on
  let footer = NSStackView(); footer.orientation = .horizontal; footer.spacing = 12
  footer.addArrangedSubview(nearby)
  printButton = NSButton(title: "macOS 인쇄창…", target: self, action: #selector(printPDF)); footer.addArrangedSubview(printButton)
  let cancel = NSButton(title: "취소", target: self, action: #selector(cancelFile)); footer.addArrangedSubview(cancel)
  save = NSButton(title: "PDF 저장", target: self, action: #selector(savePDF)); save.bezelStyle = .rounded; save.keyEquivalent = "\r"; footer.addArrangedSubview(save); root.addArrangedSubview(footer)
  for row in [header, options, footer] { row.widthAnchor.constraint(equalTo: root.widthAnchor, constant: -40).isActive = true }
  preview.widthAnchor.constraint(equalTo: root.widthAnchor, constant: -40).isActive = true; preview.heightAnchor.constraint(greaterThanOrEqualToConstant: 330).isActive = true
  enable(false); show()
 }
 func show() { NSApp.activate(ignoringOtherApps: true); window?.makeKeyAndOrderFront(nil) }
 func enable(_ ready: Bool) { save?.isEnabled = ready; printButton?.isEnabled = ready; layout.isEnabled = ready; first.isEnabled = ready; last.isEnabled = ready }
 @objc func convertToPDF(_ pasteboard: NSPasteboard, userData: String?, error: AutoreleasingUnsafeMutablePointer<NSString?>) {
  let urls = pasteboard.readObjects(forClasses: [NSURL.self], options: [.urlReadingFileURLsOnly:true]) as? [URL] ?? []
  let paths = pasteboard.propertyList(forType: NSPasteboard.PasteboardType("NSFilenamesPboardType")) as? [String] ?? []
  enqueue(urls.isEmpty ? paths.map { URL(fileURLWithPath: $0) } : urls)
 }
 func application(_ application: NSApplication, open urls: [URL]) { enqueue(urls) }
 func enqueue(_ urls: [URL]) { queue.append(contentsOf: urls.filter { $0.isFileURL }); if window != nil && !busy { doc = nil; next() }; show() }
 func next() {
  guard !queue.isEmpty else { return }
  source = queue.removeFirst(); let input = source!; busy = true; doc = nil; enable(false); preview.document = nil
  status.stringValue = "변환 중: \(input.lastPathComponent) · 로컬 변환 엔진 처리 중"; show()
  let job = ConversionJob(); currentJob = job
  DispatchQueue.global(qos: .userInitiated).async {
   let result = Result { try convert(input,job:job) }
   DispatchQueue.main.async {
    self.busy = false; self.currentJob = nil
    switch result {
    case .success(let pdf): self.doc = pdf; self.first.stringValue = "1"; self.last.stringValue = String(pdf.pageCount); self.layout.selectItem(at: 0); self.preview.document = pdf; self.enable(true); self.status.stringValue = "\(input.lastPathComponent) · \(pdf.pageCount)페이지" + (["hwp","hwpx"].contains(input.pathExtension.lowercased()) ? " · 한글: 수식·차트·복잡한 서식을 확인하세요" : "")
    case .failure(let e): self.status.stringValue = "변환 실패: \(input.lastPathComponent)"; self.alert(e.localizedDescription); self.next()
    }; self.show()
    if let page = self.preview.document?.page(at:0) { self.preview.go(to:page) }
   }
  }
 }
 @objc func choose(_ sender: Any?) {
  guard !busy else { return }
  let panel = NSOpenPanel(); panel.canChooseDirectories = false; panel.allowsMultipleSelection = true; panel.message = "PDF로 변환할 문서나 이미지를 선택하세요."
  if panel.runModal() == .OK { enqueue(panel.urls) }
 }
 func output() throws -> PDFDocument {
  guard let d = doc, let a = Int(first.stringValue.trimmingCharacters(in: .whitespaces)), let b = Int(last.stringValue.trimmingCharacters(in: .whitespaces)) else { throw fail("시작·끝 페이지를 숫자로 입력해 주세요.") }
  return try selectedPDF(d, first: a, last: b, layout: layout.indexOfSelectedItem)
 }
 @objc func refresh() { do { preview.document = try output() } catch { alert(error.localizedDescription) } }
 @objc func savePDF() {
  do {
   let result = try output(); guard let input = source else { return }
   var target = adjacentTarget(input)
   var replace = false
   if nearby.state != .on {
    let panel = NSSavePanel(); panel.allowedContentTypes = [.pdf]; panel.directoryURL = input.deletingLastPathComponent(); panel.nameFieldStringValue = target.lastPathComponent
    if input.pathExtension.lowercased() == "pdf" { panel.nameFieldStringValue = input.deletingPathExtension().lastPathComponent + " (변환).pdf" }
    guard panel.runModal() == .OK, let chosen = panel.url else { return }; target = chosen; replace = true
    guard target.resolvingSymlinksInPath().standardizedFileURL != input.resolvingSymlinksInPath().standardizedFileURL else { throw fail("원본 PDF와 다른 이름으로 저장해 주세요.") }
   }
   try writePDF(result,to:target,replacing:replace)
   NSWorkspace.shared.activateFileViewerSelecting([target])
   status.stringValue = "저장 완료: \(target.lastPathComponent)"; doc = nil; enable(false)
   if !queue.isEmpty { next() }
  } catch { alert(error.localizedDescription) }
 }
 @objc func printPDF() {
  do {
   let result = try output(); let info = NSPrintInfo.shared.copy() as! NSPrintInfo
   guard let op = result.printOperation(for: info, scalingMode: .pageScaleToFit, autoRotate: true) else { throw fail("인쇄창을 열지 못했습니다.") }
   op.printPanel.options.formUnion([.showsOrientation,.showsPaperSize,.showsPageRange,.showsPreview,.showsScaling]); op.run()
  } catch { alert(error.localizedDescription) }
 }
 @objc func cancelFile() { if busy { currentJob?.cancel(); status.stringValue = "변환 취소 중…"; return }; doc = nil; preview.document = nil; enable(false); if queue.isEmpty { window.orderOut(nil) } else { next() } }
 func applicationWillTerminate(_ notification:Notification) { currentJob?.cancel() }
 func windowShouldClose(_ sender:NSWindow) -> Bool { currentJob?.cancel(); return true }
 @objc func help() { if let url = Bundle.main.resourceURL?.appendingPathComponent("사용 안내.html") { NSWorkspace.shared.open(url) } }
 func installQuickAction() throws {
  guard let template = Bundle.main.resourceURL?.appendingPathComponent("PDF화.workflow"), FileManager.default.fileExists(atPath:template.path) else { throw fail("우클릭 메뉴 템플릿이 없습니다.") }
  let services = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Services",isDirectory:true)
  let target = services.appendingPathComponent("PDF화.workflow",isDirectory:true)
  try FileManager.default.createDirectory(at:services,withIntermediateDirectories:true)
  if !FileManager.default.fileExists(atPath:target.path) { try FileManager.default.copyItem(at:template,to:target) }
  let installedInfo = try PropertyListSerialization.propertyList(from:Data(contentsOf:target.appendingPathComponent("Contents/Info.plist")),format:nil) as? [String:Any]
  guard installedInfo?["CFBundleIdentifier"] as? String == "local.topdf.quickaction" else { throw fail("같은 이름의 다른 우클릭 메뉴가 있어 덮어쓰지 않았습니다.") }
  let workflow = template.appendingPathComponent("Contents/document.wflow")
  var plist = try PropertyListSerialization.propertyList(from:Data(contentsOf:workflow),format:nil) as! [String:Any]
  var actions = plist["actions"] as! [[String:Any]]
  var action = actions[0]["action"] as! [String:Any]
  var parameters = action["ActionParameters"] as! [String:Any]
  let quoted = "'" + Bundle.main.bundleURL.path.replacingOccurrences(of:"'",with:"'\\''") + "'"
  parameters["COMMAND_STRING"] = "/usr/bin/open -a " + quoted + " -- \"$@\""
  action["ActionParameters"] = parameters; actions[0]["action"] = action; plist["actions"] = actions
  let data = try PropertyListSerialization.data(fromPropertyList:plist,format:.xml,options:0)
  try data.write(to:target.appendingPathComponent("Contents/document.wflow"),options:.atomic)
  NSUpdateDynamicServices()
  let update = Process(); update.executableURL = URL(fileURLWithPath:"/System/Library/CoreServices/pbs"); update.arguments = ["-update"]; try update.run()
 }
 func alert(_ s: String) { show(); let a = NSAlert(); a.messageText = "PDF 변환"; a.informativeText = s; a.addButton(withTitle: "확인"); a.runModal() }
}
if CommandLine.arguments.count == 4 && CommandLine.arguments[1] == "--convert-test" {
 do {
  let d = try convert(URL(fileURLWithPath: CommandLine.arguments[2]))
  try writePDF(d,to:URL(fileURLWithPath:CommandLine.arguments[3]),replacing:true)
  print("Converted: \(d.pageCount) pages")
  exit(0)
 } catch { fputs(error.localizedDescription + "\n", stderr); exit(1) }
}
if CommandLine.arguments.count == 7 && CommandLine.arguments[1] == "--render-test" {
 do {
  guard let doc = PDFDocument(url:URL(fileURLWithPath:CommandLine.arguments[2])), let first=Int(CommandLine.arguments[4]), let last=Int(CommandLine.arguments[5]), let layout=Int(CommandLine.arguments[6]) else { throw fail("잘못된 테스트 입력") }
  let result = try selectedPDF(doc,first:first,last:last,layout:layout)
  try writePDF(result,to:URL(fileURLWithPath:CommandLine.arguments[3]),replacing:true)
  print("Rendered: \(result.pageCount) pages"); exit(0)
 } catch { fputs(error.localizedDescription + "\n",stderr); exit(1) }
}
let app = NSApplication.shared
let delegate = AppDelegate(); app.delegate = delegate; app.setActivationPolicy(.regular)
let menu = NSMenu(); let item = NSMenuItem(); menu.addItem(item); let sub = NSMenu(); sub.addItem(withTitle: "PDF로 변환 종료", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"); item.submenu = sub; app.mainMenu = menu
app.run()
