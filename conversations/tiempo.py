import time
from datetime import date
today = date.today()

#today == date.fromtimestamp(time.time())

print (today)

my_birthday = date(today.year, 6, 24)
print (my_birthday)
if my_birthday < today:
    my_birthday = my_birthday.replace(year=today.year + 1)


time_to_birthday = abs(my_birthday - today)
print (time_to_birthday.days)