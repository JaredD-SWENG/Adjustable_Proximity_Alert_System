import RPi.GPIO as GPIO
import time
from smbus import SMBus
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD
from threading import Thread
from ADCDevice import *

# Global constants
TRIG = 23
ECHO = 24
BUZZER = 17
BUTTON = 25
POT = 18

# Global variables
alarm_active = False
value = 0
distances = []
pot_values = []

# Set up GPIO mode
def setup_gpio():
    GPIO.setmode(GPIO.BCM)

def setup_gpio_pins():
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    GPIO.setup(BUZZER, GPIO.OUT)
    GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(POT, GPIO.IN)

# Initialize ADC
def setup_adc():
    global adc
    adc = ADCDevice()  # Define an ADCDevice class object
    if adc.detectI2C(0x48):  # Detect the pcf8591.
        adc = PCF8591()
    elif adc.detectI2C(0x4b):  # Detect the ads7830
        adc = ADS7830()
    else:
        print("No correct I2C address found, \n"
              "Please use command 'i2cdetect -y 1' to check the I2C address! \n"
              "Program Exit. \n")
        exit(-1)

# Initialize LCD
def setup_lcd():
    global lcd, mcp
    PCF8574_address = 0x27  # I2C address of the PCF8574 chip.
    PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.
    try:
        mcp = PCF8574_GPIO(PCF8574_address)
    except:
        try:
            mcp = PCF8574_GPIO(PCF8574A_address)
        except:
            print('I2C Address Error!')
            exit(1)
    lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4, 5, 6, 7], GPIO=mcp)

# Measure distance using the ultrasonic sensor
def measure_distance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    distance = round(distance, 2)
    return distance

# ADC data acquisition loop
def loop_adc():
    global value
    while True:
        value = adc.analogRead(0)  # read the ADC value of channel 0
        time.sleep(0.1)

# Update GUI with real-time data
def update_gui():
    global distances, pot_values, alarm_active
    distance = measure_distance()
    threshold = value * 0.5
    distances.append(distance)
    pot_values.append(threshold)
    if len(distances) > 50:  # Display last 50 data points
        distances.pop(0)
        pot_values.pop(0)

    lcd.clear()
    mcp.output(3, 1)
    if alarm_active:
        lcd.message(f"D:{distance:.1f} | T:{threshold:.1f}\n    WARNING!")
    else:
        lcd.message(f"D:{distance:.1f} | T:{threshold:.1f}")

    ax1.clear()
    ax1.plot(distances, label='Distance', color='b')
    ax1.plot(pot_values, label='Threshold', color='r')
    ax1.legend(loc='upper right')
    ax1.set_title('Real-time Distance & Threshold Values')

    if distance < threshold:
        alarm_active = True
        warning_label.config(text="WARNING!", background="red")
        GPIO.output(BUZZER, True)
    if not alarm_active:
        alarm_active = False
        warning_label.config(text="", background="lightgrey")
        GPIO.output(BUZZER, False)
    canvas.draw()

    root.after(200, update_gui)  # Refresh rate of 200ms

# Reset the alarm
def reset_alarm():
    global alarm_active
    alarm_active = False
    GPIO.output(BUZZER, False)
    warning_label.config(text="", background="lightgrey")

# Set up the GUI
def setup_gui():
    global root, fig, ax1, canvas, reset_button, warning_label
    root = tk.Tk()
    root.title("Distance Detection System")

    frame = ttk.Frame(root)
    frame.grid(row=0, column=0, sticky='w')

    fig = Figure(figsize=(8, 4))
    ax1 = fig.add_subplot(1, 1, 1)

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.grid(row=0, column=0, pady=20, padx=20)

    reset_button = ttk.Button(root, text="Reset Alarm", command=reset_alarm)
    reset_button.grid(row=1, column=0)

    warning_label = ttk.Label(root, text="", font=("Arial", 12), background="lightgrey")
    warning_label.grid(row=2, column=0, pady=20)

# Monitor button state in a separate thread
def button_monitor():
    global alarm_active
    while True:
        if GPIO.input(BUTTON) == GPIO.LOW:
            alarm_active = False
        time.sleep(0.1)  # Adjust the sleep duration as needed

# Main function
def main():
    try:
        setup_gpio()
        setup_gpio_pins()
        setup_adc()
        setup_lcd()
        setup_gui()

        button_thread = Thread(target=button_monitor)
        button_thread.daemon = True
        button_thread.start()

        adc_thread = Thread(target=loop_adc)
        adc_thread.daemon = True
        adc_thread.start()

        update_gui()
        root.mainloop()

    except KeyboardInterrupt:
        adc.close()
        pass

    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
