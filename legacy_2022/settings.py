#importation des modules 
from load_images_and_levels import load_level,load_img

#chargement du niveau courant,la valeur de (x) indique le numéro du niveau à charger  
import sys
level_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1  # Default level 1
level = load_level(x=level_num)
#chargement des images 
images=load_img()
#configuration de l'écran d'affichage 
screen_height=704
screen_width=1368
fps=60 #configuration du pas de mise à jour de l'écran 


#configuration du sol

tile_size=44
ground_numbers={0,1,2,3,4,5,10,11,12}
ramp_right_numbers={9,8}
ramp_left_numbers={6,7}
mario_number=13