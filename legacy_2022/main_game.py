#importation des modules 
import pygame as pg
from settings import*
from setup import*
#initialisation de pygame
pg.init()
#configuration de la fenetre d'affichage
screen=pg.display.set_mode((screen_width,screen_height))
surface=pg.display.set_caption("SuperMario")
#gestion des frames 
clock=pg.time.Clock()
game=Game(screen)
#création de la boucle tantque du jeu
while True:
    for event in pg.event.get():
        if event.type==pg.QUIT:
            pg.quit()
            exit()
    screen.fill("black")
    game.run()

    pg.display.update()
    clock.tick(fps)