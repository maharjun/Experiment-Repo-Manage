# Unit Test 1
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
list
