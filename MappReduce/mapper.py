#!/usr/bin/env python

import sys #Para leer entradas y salidas

for linea in sys.stdin:
    linea = linea.strip() #quita tos los espacios de la derecha he izquierda '\0'
    palabras = linea.split()

    for palabra in palabras:
        print '%s\t%s' % (palabra,1)
