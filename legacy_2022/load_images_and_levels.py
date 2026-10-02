import csv
import pygame as pg
pg.init()
screen_height=740
screen_width=1100
screen=pg.display.set_mode((screen_width,screen_height))

#some parameters
TILE_TYPES = 14  # can change manually as you add/remove tiles
TILE_SIZE = 44   # can change manually


#stocking images in a dictionary (keys represent images' names)
def load_img():
    images={}
    for x in range(TILE_TYPES):
        img = pg.image.load(f'img/tile/{x}.png').convert_alpha()
        #img = pg.transform.scale(img, (TILE_SIZE, TILE_SIZE))
        images[f'{x}.png'] = img
    return (images)



#loading maps after desining and saving them in 'preloaded_levels' folder from the level creator
def load_level(x):
    world_data = []
    for row in range(16):
        r = [-1] * 300
        world_data.append(r)
    # load in level data and create world
    with open(f'level{x}_data.csv', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for x, row in enumerate(reader):
            for y, tile in enumerate(row):
                world_data[x][y] = int(tile)
    return (world_data)

