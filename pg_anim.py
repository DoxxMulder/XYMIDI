#!/usr/bin/python
import pygame as pg
from pygame.locals import *
import mido
import pygame_menu as pm
import sys
import numpy as np
import platform

#Simple animation in pygame. Hopefully.

pg.init()

DOUBLECLICKTIME = 250
WAITTIME = 2000


size = width, height = 480, 320
bgcolor = 0, 0, 0

screen = pg.display.set_mode(size, pg.RESIZABLE, pg.FULLSCREEN)
surf = pg.Surface(screen.get_size())
surf = surf.convert()
surf.fill(bgcolor)
clock = pg.time.Clock()
dcClock = pg.time.Clock()


def color_change(image, color):
    clrImg = pg.Surface(image.get_size())
    clrImg.fill(color)
    fnlImg = image.copy()
    fnlImg.blit(clrImg, (0,0), special_flags=pg.BLEND_MULT)
    return fnlImg

class midiData(object): #Really this should be a struct, but this is Python so...
    def __init__(self):
        self.selected_dvc = 0   #Whammy in 'Classic' mode
        self.selected_cnl = 9   #Whammy defaults to accepting midi input on channel 10 only
        self.selected_pgm = 21  #In order to rectify the different ways of writing the pgm number, this will match the Whammy pdf, and will be "X - 1" when used
        self.selected_cc = 11   #MIDI CC 11 == expression pedal. Do not modify for Whammy control.
        self.pgms = [ 'H +/- Oct',21,
                'H -5th -4th',20,
                'H -4th -3rd', 19,
                'H 5th 7th',18,
                'H 5th 6th',17,
                'H 4th 5th',16,
                'H 3rd 4th',15,
                'H 3brd 3rd',14,
                'H 2nd 3rd',13,
                'DT Shallow',12,
                'DT Deep',11,
                '+2 Oct',1,
                '+ Oct',2,
                '5th',3,
                '4th',4,
                '-2nd',5,
                '-4th',6,
                '-5th',7,
                '- Oct',8,
                '-2 Oct',9,
                'Dive',10,]

    def set_dvc(self, _, num):
        self.selected_dvc = num

    def set_cnl(self, _, num):
        self.selected_cnl = num

    def set_pgm(self, _, num):
        if (self.selected_dvc % 2) == 0:    #Adding an offset of 42 maps to the 'chords' algorithms
            self.selected_pgm = num
        else:
            self.selected_pgm = num + 42

    def set_cc(self, _, num):
        self.selected_cc = num

    def get_dvc(self):
        return self.selected_dvc

    def get_cnl(self):
        return self.selected_cnl

    def get_pgm(self):
        return self.selected_pgm
    
    def get_pgmi(self):
        return (self.pgms.index(self.selected_pgm)//2)
    
    def get_cc(self):
        return self.selected_cc


def menu_init(mididata):
    menu = pm.Menu('Options', width, height, theme=pm.themes.THEME_SOLARIZED, onclose=pm.events.CLOSE)
    selector_device=menu.add.selector(
        title='Midi Device: ',
        items=[('Whammy: Classic', 0), ('Whammy: Chords', 1)],
        font_size=14,
        default=mididata.get_dvc(),
        onchange=mididata.set_dvc
    )
    selector_cnl=menu.add.dropselect(
        title='Channel: ',
        items=[ ('1',0),
                ('2',1),
                ('3',2),
                ('4',3),
                ('5',4),
                ('6',5),
                ('7',6),
                ('8',7),
                ('9',8),
                ('10',9),
                ('11',10),
                ('12',11),
                ('13',12),
                ('14',13),
                ('15',14),
                ('16',15),],
        font_size=14,
        default=mididata.get_cnl(),
        selection_box_height=10,
        selection_box_width=50,
        selection_option_font_size=14,
        onchange=mididata.set_cnl
    )    
    selector_pgm=menu.add.dropselect(
        title='Whammy setting: ',
        items=[ ('H +/- Oct',21),
                ('H -5th -4th',20),
                ('H -4th -3rd', 19),
                ('H 5th 7th',18),
                ('H 5th 6th',17),
                ('H 4th 5th',16),
                ('H 3rd 4th',15),
                ('H 3brd 3rd',14),
                ('H 2nd 3rd',13),
                ('DT Shallow',12),
                ('DT Deep',11),
                ('+2 Oct',1),
                ('+ Oct',2),
                ('5th',3),
                ('4th',4),
                ('-2nd',5),
                ('-4th',6),
                ('-5th',7),
                ('- Oct',8),
                ('-2 Oct',9),
                ('Dive',10),],
        font_size=14,
        default=mididata.get_pgmi(),
        selection_box_height=10,
        selection_box_width=180,
        selection_option_font_size=12,
        open_middle=True,
        onchange=mididata.set_pgm
    )    
    menu.add.button('Quit', pm.events.EXIT, align=pm.locals.ALIGN_RIGHT, font_size=14)
    menu.mainloop(screen)

def xy_midi(x,y,outport, mididata):
    x = int(x)
    y = int(y)
    
    #Scale XY to usable data
    #TODO: Add flag to reverse MIDI values for specific PGMs so up always means up in pitch

    if x < 48:
        x_scale = 127
    elif (x >= 48) and (x <= 220):
        x_scale = np.rint(127 - ((x-48)*(64/172)))
    elif (x > 220) and (x < 260):
        x_scale = 63
    elif (x >= 260) and (x <= 432):
        x_scale = np.rint(63-((x-260)*(63/172)))
    else:
        x_scale = 0

    if y < 32:
        y_scale = 0
    elif (y >= 32) and (y <= 150):
        y_scale = np.rint((y-32)*(63/118))
    elif (y > 150) and (y < 170):
        y_scale = 63
    elif (y >= 170) and (y <= 288):
        y_scale = np.rint(64+(y-170)*(64/118))
    else:
        y_scale = 127
    x_scale = int(x_scale)
    y_scale = int(y_scale)
    #print("Old: ", x, ", ", y, " New: ",x_scale,", ", y_scale)

    if y_scale <= 16:   #Turn off whammy if selection too close to bridge
        pgm = mididata.get_pgm() + 20 #-1 to rectify, +21 to turn off effect
    else:
        pgm = mididata.get_pgm() - 1
    
    #msg_off = mido.Message('note_off',note=60, velocity=0)
    #msg_on = mido.Message('note_off',note=60, velocity=64)
    msg_pgm = mido.Message('program_change', channel=mididata.get_cnl(), program=pgm)
    msg_cc = mido.Message('control_change', channel=mididata.get_cnl(), control=mididata.get_cc(), value=x_scale)
    
    #outport.send(msg_off)
    #outport.send(msg_on)
    outport.send(msg_pgm)
    outport.send(msg_cc)
    #print(msg_cc)


def main():
    hue = 0
    sx = width/2
    sy = height/2


    img = pg.image.load('glow.bmp').convert_alpha()
    img = pg.transform.rotozoom(img, 0, 2)
    rect = img.get_rect()
    rect.center = sx, sy
    moving = False
    pg.mouse.set_visible(False)

    #print(mido.get_output_names())
    #print(mido.get_input_names())

    os = platform.system()

    try:
        if os == 'Windows':     #Open (my) default MIDI outputs as appropriate
            outport = mido.open_output('UMC1820 MIDI Out 1')
        else:
            outport = mido.open_output('CH345:CH345 MIDI 1 20:0')
    except:
        outports_list = mido.get_output_names()
        outport = mido.open_output(outports_list[1])       

    #inport = mido.open_input('UMC1820 MIDI In 0')

    mdata = midiData()

    while 1:
        clock.tick(60)
        for event in pg.event.get():

            if event.type == pg.QUIT: sys.exit()
            elif event.type == MOUSEBUTTONDOWN:
                if dcClock.tick() < DOUBLECLICKTIME:
                    #pg.mouse.set_visible(True)
                    menu_init(mdata)
                moving = True
                rect.center = pg.mouse.get_pos()
                sx, sy = pg.mouse.get_pos()
            elif event.type == MOUSEBUTTONUP:
                moving = False
            elif event.type == MOUSEMOTION and moving:
                rect.move_ip(event.rel)
                sx, sy = rect.center
        
        xy_midi(sx, sy, outport, mdata)
        pg.mouse.set_visible(False)
        color = pg.Color(0)
        color.hsla = (hue, 100, 50, 100)
        hue = hue + 1 if hue < 360 else 0
        cImg = color_change(img, color)
        
        screen.fill(bgcolor)
        screen.blit(cImg, rect)

        pg.display.flip()

if __name__ == "__main__":    
	main()