#!/usr/bin/env python3

import argparse
import os
import sys
import time
import logging
import glob
from collections import OrderedDict
import subprocess

import cv2
from pyzbar import pyzbar

LOG = logging.getLogger(name="find-my-parcel")


def normlize_barcode(barcode):
    return barcode.strip().upper().replace("-", "")


def speak(words):
    subprocess.check_call(["espeak", "-a", "150", words])


def load_parcels():
    root = "parcels/"
    items = []  # [(code0, owner0), (code1, owner1), ...]
    stats = {}
    for filename in os.listdir(root):
        if filename.endswith(".txt"):
            filepath = os.path.join(root, filename)
            if os.path.isfile(filepath) and not filepath.startswith("."):
                owner = filename.split(".")[0]
                count = 0
                with open(filepath) as fileobj:
                    for line in fileobj:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            barcode = normlize_barcode(line.split()[0])
                            items.append((barcode, owner))
                            count += 1
                stats[owner] = count
    print("total: {}".format(len(items)))
    for owner, count in stats.items():
        print("{}: {}".format(owner, count))
    ordered_items = sorted(items, key=lambda item: len(item[0]), reverse=True)
    return OrderedDict(ordered_items)


def find_owner(parcels, raw_barcode, unknown="unknown"):
    barcode = normlize_barcode(raw_barcode)
    LOG.info("barcode detected and normalized: {} -> {}".format(raw_barcode, barcode))
    # full match
    owner = parcels.get(barcode, "")
    if owner:
        LOG.info("barcode full match: {} -> {}".format(barcode, owner))
        return owner

    # loaded barcode is partial of scanned barcode
    for item, owner in parcels.items():
        if item in barcode:
            LOG.info("barcode partial match: {} -> {} -> {}".format(barcode, item, owner))
            return owner

    LOG.info("barcode not match: {} -> {}".format(barcode, unknown))
    return unknown


def read_barcodes(frame, parcels):
    barcodes = pyzbar.decode(frame)
    for barcode in barcodes:
        x, y, w, h = barcode.rect
        barcode_info = barcode.data.decode('utf-8')
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, barcode_info, (x + 6, y - 6), font, 2.0, (255, 255, 255), 1)
        owner = find_owner(parcels, barcode_info)
        speak(owner)
        time.sleep(1.0)
    return frame


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Find My Parcel')

    parser.add_argument(
        '-v', '-verbose', dest='verbose', action='store_true',
        help='print verbose log')

    parser.add_argument(
        '-i', '--vedio-device-id', dest='video_device_id', type=int,
        help='video device id from `ls /dev/video*`')

    parser.add_argument(
        '-l', '-list-parcels', dest='list_parcels', action='store_true',
        help='list loaded parcels')

    args = parser.parse_args()

    logging.basicConfig(
        level="DEBUG" if args.verbose else "INFO",
        format="%(asctime)s - %(levelname)s: %(message)s",
    )

    parcels = load_parcels()
    if args.list_parcels:
        for barcode, owner in parcels.items():
            print("{} -> {}".format(barcode, owner))
        return

    video_device_id = args.video_device_id
    if video_device_id is None:
        video_devices = glob.glob("/dev/video*")
        if not video_devices:
            LOG.error("no video device found, exit")
            sys.exit()
        if len(video_devices) > 1:
            subprocess.check_call(["v4l2-ctl", "--list-devices"])
            LOG.warning("multiple video devices found, please specify id")
            sys.exit()
        else:
            video_device_id = int(video_devices[0][-1])

    camera = cv2.VideoCapture(video_device_id)
    ret, frame = camera.read()
    while ret:
        ret, frame = camera.read()
        frame = read_barcodes(frame, parcels)
        cv2.imshow('Barcode/QR code reader', frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break
    camera.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
