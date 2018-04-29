#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

#
# Albow - Sound utilities
#

import pygame
from pygame import mixer


def pause_sound():
    try:
        mixer.pause()
    except pygame.error:
        pass


def resume_sound():
    try:
        mixer.unpause()
    except pygame.error:
        pass


def stop_sound():
    try:
        mixer.stop()
    except pygame.error:
        pass
