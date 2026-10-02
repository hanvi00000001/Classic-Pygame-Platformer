import pygame as pg


#création de la classe Mario
class Mario(pg.sprite.Sprite):
    def __init__(self,pos):
        super().__init__()
        self.max_health=3
        self.size=(40,60)
        #configuration des mode de Mario
        self.fire=False
        self.big=False
        self.small=True
        self.tiny=False
        #configuration du mouvement
        self.speed=8
        self.jump_height=-20
        self.gravity=1.2
        self.direction=pg.math.Vector2(0,0)
        #configuration de l'etat
        self.facing_right=True
        self.status="idle"
        self.on_ground=False
        self.on_left_ramp=False
        self.on_right_ramp=False
        #chargement de l'image
        self.image=pg.Surface(self.size)
        self.image.fill("red")
        self.rect=self.image.get_rect(topleft=pos)
    #récuperation des touches du clavier    
    def input(self):
        keys = pg.key.get_pressed()
        if keys[pg.K_RIGHT]:
            self.direction.x=1
            self.facing_right=True
        elif keys[pg.K_LEFT]:
            self.direction.x=-1
            self.facing_right=False
        else:
            self.direction.x=0
        if keys[pg.K_SPACE] and (self.on_ground or self.on_right_ramp or self.on_left_ramp):
            self.jump()
    #création de la gravité
    def creat_gravity(self):
        self.direction.y+=self.gravity
        self.rect.y+=self.direction.y
    #sauter
    def jump(self):
        if self.on_ground:
            self.direction.y=self.jump_height
            self.on_ground=False
    def update(self):
        self.input()
    