from gpiozero import Servo, AngularServo
from time import sleep

servo = AngularServo(14)


def unlock(angle):
     '''
     angle - the angle to set the servo at UNLOCK position
     '''
     servo.angle = angle

def lock(angle):
     '''
     angle - the angle to set the servo at LOCK position
     '''
     servo.angle = angle

def timer_lock(lock_angle, unlock_angle, time):
     '''
     time - the time that you want to keep the lock locked for
     '''
     #the 0 and 90 in the lock and unlock methods can be changed
     lock(lock_angle)
     sleep(time)
     unlock(unlock_angle)


if __name__ == "__main__":
    

