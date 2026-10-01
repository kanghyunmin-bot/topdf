on run argv
set inputPath to item 1 of argv
set outputPath to item 2 of argv
with timeout of 180 seconds
 tell application "Pages"
  set docRef to open (POSIX file inputPath)
  try
   export docRef to (POSIX file outputPath) as PDF
  on error msg number n
   close docRef saving no
   error msg number n
  end try
  close docRef saving no
 end tell
end timeout
end run
