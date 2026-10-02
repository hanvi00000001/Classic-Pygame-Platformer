import pygame as pg 
from caracters import*
from objects import*
from settings import *

#création de la classe Game 
class Game:
    def __init__(self,display_window):
        self.world_shift=0
        self.display_window=display_window
        self.player_group=pg.sprite.GroupSingle()
        self.tile_group=pg.sprite.Group()
        self.ramp_right_group=pg.sprite.Group()
        self.ramp_left_group=pg.sprite.Group()
        
        self.creat_objects()

    def creat_objects(self):
        for i in range(len(level)):
            for j in range(len(level[i])):
                x=j*tile_size
                y=i*tile_size
                if level[i][j] in ground_numbers:
                    tile=Ground(tile_size,(x,y),level[i][j])
                    self.tile_group.add(tile)
                elif level[i][j] in ramp_right_numbers:
                    ramp_right=Ground(tile_size,(x,y),level[i][j])
                    self.ramp_right_group.add(ramp_right)
                elif level[i][j] in ramp_left_numbers:
                    ramp_left=Ground(tile_size,(x,y),level[i][j])
                    self.ramp_left_group.add(ramp_left)
                elif level[i][j]==mario_number:
                    mario=Mario((x,y))
                    self.player_group.add(mario)
    def horizontal_movement_collision(self):
        player=self.player_group.sprite
        player.rect.x += player.direction.x * player.speed
        for tile in self.tile_group.sprites():
            if tile.rect.colliderect(player.rect):
                if player.direction.x < 0: 
                    player.rect.left = tile.rect.right
                    player.direction.x=0
                elif player.direction.x>0:
                    player.rect.right=tile.rect.left
                    player.direction.x=0
    
		
    def vertical_movement_collision(self):
        player=self.player_group.sprite
        player.creat_gravity()
        for tile in self.tile_group.sprites():
            if tile.rect.colliderect(player.rect):
                if player.direction.y < 0:
                    player.rect.top=tile.rect.bottom
                    player.direction.y=0
                    player.on_ground=False
                elif player.direction.y>0:
                    player.rect.bottom=tile.rect.top
                    player.on_ground=True
                    player.direction.y=0
    
    def left_ramp_collision(self):
        player=self.player_group.sprite
        collide=False
        for ramp in self.ramp_left_group.sprites():
            if ramp.rect.colliderect(player.rect):
                if player.rect.bottomleft[1]>player.rect.x+ramp.rect.topleft[1]-ramp.rect.topleft[0]:
                    player.rect.y=player.rect.x+ramp.rect.topleft[1]-ramp.rect.topleft[0]-player.size[1]
                    collide=True        
        if collide==False:
            player.on_left_ramp=False
        else:
            player.on_left_ramp=True

    def right_ramp_collision(self):
        player=self.player_group.sprite
        collide=False
        for ramp in self.ramp_right_group.sprites():
            if ramp.rect.colliderect(player.rect):
                if player.rect.bottomright[1]>-player.rect.bottomright[0]+ramp.rect.bottomleft[1]+ramp.rect.bottomleft[0]-player.size[1]:
                    player.rect.y=-player.rect.bottomright[0]+ramp.rect.bottomleft[1]+ramp.rect.bottomleft[0]-player.size[1]
                    collide=True 
        if collide==False:
            player.on_right_ramp=False
        else:
            player.on_right_ramp=True
    def scroll_x(self):
        player=self.player_group.sprite
        player_x=player.rect.x
        if player_x<=500 and player.direction.x<0:
            self.world_shift=8
            player.speed=0
        elif player_x>=868 and player.direction.x>0:
            self.world_shift=-8
            player.speed=0
        else:
            player.speed=8
            self.world_shift=0




    def run(self):
        self.ramp_right_group.update(self.world_shift)
        self.ramp_right_group.draw(self.display_window)
        self.ramp_left_group.update(self.world_shift)
        self.ramp_left_group.draw(self.display_window)
        #affichage et mise à jour du sol
        self.tile_group.update(self.world_shift)
        self.tile_group.draw(self.display_window)
        #mise à jour de la méthode collision
        #affichage et mise à jour du joueur principale
        self.player_group.update()
        self.horizontal_movement_collision()
        self.vertical_movement_collision()
        self.left_ramp_collision()
        self.right_ramp_collision()
        self.scroll_x()
        self.player_group.draw(self.display_window)
        

       




        