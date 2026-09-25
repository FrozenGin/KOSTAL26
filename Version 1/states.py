from enum import Enum

class Dir(Enum):
    
    STOP = 0

    FORWARD = 1

    LEFT = 2

    RIGHT = 3

    BACKWARDS = 4

    WHITE = 5

class SENSORSTATE(Enum):

        BLACK = 0
        WHITE = 1
        FORWARD = 2
        BACKWARD = 3
        LEFT = 4
        RIGHT = 5
        HARDLEFT = 6
        HARDRIGHT = 7