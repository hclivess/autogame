import classes

for x in classes.enemies:
    print (x().trigger)
    print(x)


for item_class in classes.items:
    print (item_class)

    if item_class == classes.Armor:
        print ("heureka")