import base64
import sys
def main():
	#decodifica en base64
	x = sys.argv[1]
	datos = base64.b64decode(x)
	print(datos)



if __name__ == '__main__':
	main()