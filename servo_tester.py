from gpiozero import Servo, AngularServo
from time import sleep

servo = AngularServo(14)


def unlock():
     servo.angle = 90

def lock():
     servo.angle = 0


if __name__ == "__main__":
    #take in user signal
    #call lock/unlock

