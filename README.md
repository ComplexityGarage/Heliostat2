# HELIOSTAT 101
# AUTHORS
Karolina Nowak
# DESCRIPTION OF THE PROJECT
The heliostat project was created for people who lack natural sunlight in the rooms they use during their morning routine.

It is a simple device that tracks the movement of the Sun and adjusts its position accordingly to reflect sunlight into a room that does not receive direct natural light. 

This project was developed by combining 3D printing with Arduino-based electronics and two micro servomotors.
The entire mechanical structure was designed in Fusion 360 and then 3D printed. Its movement is controlled by an Arduino board connected to two servomotors able to move in two different axes, while the computer is using Pysolar, a Python library that allows sun-tracking, and transmits the calculated data to the Arduino, which translates it into precise movements of the two servomotors.

The Heliostat project was made having in mind a balance between simplicity and functionality.
# SCIENCE & TECH USED
Heliostat operates based on the fundamental law of reflection: the angle of incidence is equal to the angle of reflection.
To redirect sunlight from the moving Sun towards a fixed target, the normal vector of the mirror must always bisect the angle between the Sun, the mirror, and the target.
To simplify - when the Sun moves by an angle α, the mirror rotates by approximately α/2 to maintain the reflected beam in the same direction.

In the python code user sets the desirable fixed target by manually defining the direction and inclination. Using the geographical location, current date and time, Pysolar calculates the Sun’s real-time azimuth and altitude. Based on these values and the predefined target direction, the program determines the required orientation of the mirror.
The oreintation is converted then to the positions the servomotors must take and then the data is transmitted to the Arduino.

To sum up the tech used:
- Arduino Uno board
- two micro servomotors MG90S (with metal mechanism)

> [!IMPORTANT]
>The Arduino board has to be permanently connected to computer for Heliostat to work.

# STATE OF THE ART

Heliostat is a mechanism that has to move the mirror in 2 axes. The designed mechanism is composed of:
- a cylindrical stand made out of two parts allowing the upper part to rotate, controlled by one of the servomotors
- two arms, placed on the upper stand, on one of them there is a place for the second servomotor
- a small cog wheel placed between arms which the servomotor moves
- a bracket holding the mirror with halth of cogwheel embedded to its structure - it connects to the smaller cogwheel and is supported by the arms

> [!NOTE]
> Heliostat works on three different modes: ZERO, NORMAL and TEST.

**ZERO** mode:

This mode is the basic calibration of the two servomotors - the mechanism is set on a deafult positions - base in the centre and the mirror positioned flat.

**NORMAL** mode:

Heliostat works automatically between 08:00 a.m. and 13:00. In these hours it calculates positions for the servos and sends it to Arduino each 20s. If the NORMAL mode is enabled after the working hours it automatically is set to mode ZERO.

**TEST** mode:

While activating this mode there are several options available:
- Manual control of the servomotors
- Switching to mode ZERO
- Checking the status of the servomotors position
- Conduct a simulation of how the Heliostat works by setting an hour between 08:00 to 13:00
# WHAT NEXT?
The project ultimately should work without the need of constant connection to the computer. 

The 3D design could be upgraded to hide the electronics underneath the stand to make it more visually stricking.

I look forward to further modifications as I feel the Heliostat needs some more pampering.

# SOURCES
- [Writing on GitHub](https://docs.github.com/en/get-started/writing-on-github)

