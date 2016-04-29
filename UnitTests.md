# Unit Test 1
clear'
clear\
clear --noconf
book dir A --inter --reltop --noconf
book dir A/B --reltop
Y
list
book exp A --n4 --reltop --noconf
book exp A/C --n4 --reltop --noconf
list
book exp A/C --n4 --force --reltop --noconf
list
unbook exp A/C --n3 --force
n
unbook exp A/C --n3 --reltop --force --noconf
list --nocolor
book exp A/B --n4 --reltop --noconf
list > TempText
confirm > TempText2
Y

book exp A/C --n3 --reltop --noconf
confirm --noconf > TempText3

book exp A/D/A --n3 --reltop --force --noconf
confirm --noconf > TempText4

book exp A/D/C --n3 --reltop --force --noconf
book exp A/D/D --n3 --reltop --force --noconf
confirm --noconf > TempText5
