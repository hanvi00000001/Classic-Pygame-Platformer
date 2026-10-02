import pygame as pg
from settings import images,tile_size  

#création de classe Tile
class Ground(pg.sprite.Sprite):
    def __init__(self,size,pos,image_number):
        super().__init__()
        image=pg.image.load(f"img/tile/{image_number}.png").convert_alpha()
        self.image=pg.transform.scale(image,(tile_size,tile_size))
        self.rect=self.image.get_rect(topleft=pos)
        self.mask=pg.mask.from_surface(self.image)
    def update(self,ground_shift):
        self.rect.x+=ground_shift

