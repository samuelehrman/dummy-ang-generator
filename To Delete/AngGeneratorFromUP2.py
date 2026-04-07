import struct

import os

 

upName = r"C:\Users\samue\Box\Code\Pattern Sharpness\20240320_27061_256x256.up2"

angName = r'C:\Users\samue\Box\Code\Pattern Sharpness\Testing\initial_test.ang'

 

# these values are hard coded and won't be overwritten from values in the UP file

xstar = 0.50

ystar = 0.70

zstar = 0.67

sTilt = 70

cElev = 10

 

# these values may be present in a newer UP file

cols = 200 # or None if unknown

rows = 200 # or None if unknown

dx = None # default, may be overwritten from file

dy = None # default, may be overwritten from file

 

# try to pull some info from the up file

with open(upName, 'rb') as file:

                hdr_fmt = '<iiiiBiiBdd' # version, pat cols, pat rows, data offset, extra pattern flag (for hex grids), scan cols, scan rows, hex/square flag, x step, y step

                hdr_len = struct.calcsize(hdr_fmt)

                hdr_bytes = file.read(hdr_len)

                if not hdr_bytes: exit(1)

                s = struct.Struct(hdr_fmt).unpack_from(hdr_bytes)

                if s[0] < 1 or s[0] > 4:

                                exit(1) # unsupported version

                                pass

                if s[0] > 2: # we have our scan dimensions

                                cols = s[5]

                                rows = s[6]

                                dx   = s[8]

                                dy   = s[9]

                else: # we don't have scan dimensions

                                fBytes = os.path.getsize(upName) - s[3]

                                pBytes = s[1] * s[2];

                                if '1' == upName[-1]:

                                                pass

                                elif '2' == upName[-1]:

                                                pBytes = pBytes * 2

                                else:

                                                exit(1) # we don't know the bit depth

                                numPats = round(fBytes / pBytes)

 

                                # we could come up with some options but otherwise stuff needs to be specified

                                if cols is None or rows is None or cols * rows != numPats:

                                                print('file containts %i patterns' % (numPats,))

                                                print('cols * rows != number of patterns')

                                                tgtSq = numPats**0.5

                                                minAspect = 0.5

                                                minX = round(tgtSq * minAspect**0.5)

                                                maxX = round(tgtSq)

                                                print('potential dimensions in %i, %i:' % (minX, maxX))

                                                candidates = []

                                                for i in range(minX, maxX+1, 1):

                                                                if 0 == numPats % i:

                                                                                candidates.append((i, round(numPats / i)))

                                                                                print('%i) %i x %i' % (len(candidates), i, round(numPats / i)))

                                                if not candidates:

                                                                print('No valid dimensions found.')

                                                                exit(1)

                                                while True:

                                                                try:

                                                                                choice = int(input('Enter the number of the dimension to use: '))

                                                                                if 1 <= choice <= len(candidates):

                                                                                                cols, rows = candidates[choice - 1]

                                                                                                print('Using %i cols x %i rows' % (cols, rows))

                                                                                                break

                                                                                else:

                                                                                                print('Please enter a number between 1 and %i.' % len(candidates))

                                                                except ValueError:

                                                                                print('Invalid input, please enter a number.')

                                if dx is None:

                                                dx = 1.

                                if dy is None:

                                                dy = 1.;

 

# now we have some values to use

with open(angName, 'w') as file:

                # write minimal header

                file.write('# x-star %f\n# y-star %f\n# z-star %f\n' % (xstar, ystar, zstar))

                file.write('# WorkingDistance 10.0\n# SampleTiltAngle %f\n# CameraElevationAngle %f\n# CameraAzimuthalAngle 0.\n' % (sTilt, cElev))

                file.write('# GRID: SqrGrid\n# XSTEP: %f\n# YSTEP: %f\n' % (dx, dy))

                file.write('# NCOLS_ODD: %i\n# NCOLS_EVEN: %i\n# NROWS: %i\n' % (cols, cols, rows))

                file.write('# Phase 1\n# MaterialName <unknown>\n# Symmetry 1\n# LatticeConstants 3. 4. 5. 70. 80. 100.\n# NumberFamilies 0\n')

 

                # now build grid points once

                x = [dx * i for i in range(cols)]

                y = [dy * i for i in range(rows)]

                for j in range(rows):

                                for i in range(cols):

                                                file.write('0. 0. 0. %f %f 0. -1.\n' % (x[i], y[j])) # phi1 PHI phi2 x y iq ci

