import aubio
import numpy as np
import pyaudio
import pygame

import argparse
# Remove music21, queue

parser = argparse.ArgumentParser()
parser.add_argument("-input", required=False, type=int, help="Audio Input Device")
parser.add_argument("-res", required=False, type=int, help="Set Game Resolution")
parser.add_argument("-width", required=False, type=int, help="Set Window Width")
parser.add_argument("-height", required=False, type=int, help="Set Widnow Height")
args = parser.parse_args()

if args.input is None:
    print("No input device specified. Printing list of input devices now: ")
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        print("Device number (%i): %s" % (i, p.get_device_info_by_index(i).get('name')))
    print("Run this program with -input 1, or the number of the input you'd like to use.")
    exit()

p = pyaudio.PyAudio()

# Open stream.
stream = p.open(format=pyaudio.paFloat32,
                channels=1, rate=44100, input=True,
                input_device_index=args.input, frames_per_buffer=4096)

clapped = pygame.event.Event(pygame.USEREVENT, attr1='clapped')

# Aubio's pitch detection.
pDetection = aubio.pitch("default", 2048, 2048//2, 44100)
# Set unit.
pDetection.set_unit("Hz")
pDetection.set_silence(-40)


def get_current_note(volume_thresh=0.1, printOut=False):
    while True:
        data = stream.read(1024, exception_on_overflow=False)
        samples = np.frombuffer(data, dtype=aubio.float_type)
        pitch = pDetection(samples)[0]

        volume = np.sum(samples**2)/len(samples) * 100

        if pitch and volume > volume_thresh:
            if pygame.get_init():
                pygame.event.post(clapped)
        else:
            continue

        if printOut:
            print("Freq: " + str(pitch))
            print(volume)

if __name__ == '__main__':
    get_current_note(volume_thresh=0.1, printOut=True)