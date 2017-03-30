#!/usr/bin/env python

from operator import itemgetter
import sys

palabra_actual = None
contador_actual = 0
palabra = None

for linea in sys.stdin:
    linea = linea.strip()
    palabra, contador = linea.split('\t',1) #quita los tabs

    try:

        contador = int(contador)
    except ValueError:
        continue
    if palabra_actual == palabra:
        contador_actual += contador
    else:
        if palabra_actual:
            print '%s\t%s' % (palabra_actual, contador_actual)
        contador_actual = contador
        palabra_actual = palabra

if palabra_actual == palabra:
    print '%s\t%s' % (palabra_actual, contador_actual)
