# python script to convert PSG VGM files to compact resampled BBC Micro files
# http://www.smspower.org/Development/SN76489#PlayingSamplesOnThePSG
# http://vgmrips.net/wiki/VGM_Specification
# http://vgmrips.net/packs/pack/svc-motm
# http://www.wothke.ch/webvgm/
# http://www.stairwaytohell.com/music/index.html?page=vgmarchive
# http://www.zeridajh.org/articles/various/sn76489/index.htm
# http://www.smspower.org/Music/Homebrew
# http://www.tommowalker.co.uk/music.html
# http://battleofthebits.org/arena/Tag/SN76489/
# http://battleofthebits.org/browser/

import gzip
import struct
import sys
import binascii
import math

if (sys.version_info > (3, 0)):
	from io import BytesIO as ByteBuffer
else:
	from StringIO import StringIO as ByteBuffer



#-----------------------------------------------------------------------------
# script vars / configs

vgm_frequency = 44100
play_frequency = 50 #50 # resample to N hz

FORCE_BBC_MODE = True # forces clock speed & register settings in output vgm. Also retunes tone frequencies if the clock speed of the VGM is different
ENABLE_RETUNE = True	# enables re-tuning of the VGM to suit different clock speeds
OPTIMIZE_COMMANDS = True # if true will optimize any redundant register writes that occur when the song is quantized
RETUNE_PERIODIC = True	# if true will attempt to retune any use of the periodic noise effect

FILTER_CHANNEL0 = False
FILTER_CHANNEL1 = False
FILTER_CHANNEL2 = False
FILTER_CHANNEL3 = False


filename = "10 Page 4.vgm"
filename = "18 - 14 Dan's Theme.vgm"
filename = "Galaforce2-title.vgm"
filename = "Firetrack-ingame.vgm"
filename = "CodenameDroid-title.vgm"
filename = "07 - 07 COOL JAM.vgm"
filename = "09 - 13 Ken's Theme.vgm"
filename = "15 Diamond Maze.vgm"
filename = "01 Game Start.vgm"

#filename = "en vard fyra javel.vgm"
filename = "MISSION76496.vgm"
#filename = "ne7-magic_beansmaster_system_psg.vgm"
#filename = "chris.vgm"
#filename = "BotB 16439 Chip Champion - frozen dancehall of the pharaoh.vgm" # pathological fail, uses the built-in periodic noises which are tuned differently

#filename = "pn.vgm"

output_filename = "test.vgm"


#-----------------------------------------------------------------------------


class VersionError(Exception):
	pass


class VgmStream:
	# VGM file identifier
	vgm_magic_number = b'Vgm '

	disable_dual_chip = True

	vgm_source_clock = 0
	vgm_target_clock = 0
	
	
	# Supported VGM versions
	supported_ver_list = [
		0x00000101,
		0x00000110,
		0x00000150,
		0x00000151,
		0x00000160,
	]

	# VGM metadata offsets
	metadata_offsets = {
		# SDM Hacked version number 101 too
		0x00000101: {
			'vgm_ident': {'offset': 0x00, 'size': 4, 'type_format': None},
			'eof_offset': {'offset': 0x04, 'size': 4, 'type_format': '<I'},
			'version': {'offset': 0x08, 'size': 4, 'type_format': '<I'},
			'sn76489_clock': {'offset': 0x0c, 'size': 4, 'type_format': '<I'},
			'ym2413_clock': {'offset': 0x10, 'size': 4, 'type_format': '<I'},
			'gd3_offset': {'offset': 0x14, 'size': 4, 'type_format': '<I'},
			'total_samples': {'offset': 0x18, 'size': 4, 'type_format': '<I'},
			'loop_offset': {'offset': 0x1c, 'size': 4, 'type_format': '<I'},
			'loop_samples': {'offset': 0x20, 'size': 4, 'type_format': '<I'},
			'rate': {'offset': 0x24, 'size': 4, 'type_format': '<I'},
			'sn76489_feedback': {
				'offset': 0x28,
				'size': 2,
				'type_format': '<H',
			},
			'sn76489_shift_register_width': {
				'offset': 0x2a,
				'size': 1,
				'type_format': 'B',
			},
			'ym2612_clock': {'offset': 0x2c, 'size': 4, 'type_format': '<I'},
			'ym2151_clock': {'offset': 0x30, 'size': 4, 'type_format': '<I'},
			'vgm_data_offset': {
				'offset': 0x34,
				'size': 4,
				'type_format': '<I',
			},
		},

		# Version 1.10`
		0x00000110: {
			'vgm_ident': {'offset': 0x00, 'size': 4, 'type_format': None},
			'eof_offset': {'offset': 0x04, 'size': 4, 'type_format': '<I'},
			'version': {'offset': 0x08, 'size': 4, 'type_format': '<I'},
			'sn76489_clock': {'offset': 0x0c, 'size': 4, 'type_format': '<I'},
			'ym2413_clock': {'offset': 0x10, 'size': 4, 'type_format': '<I'},
			'gd3_offset': {'offset': 0x14, 'size': 4, 'type_format': '<I'},
			'total_samples': {'offset': 0x18, 'size': 4, 'type_format': '<I'},
			'loop_offset': {'offset': 0x1c, 'size': 4, 'type_format': '<I'},
			'loop_samples': {'offset': 0x20, 'size': 4, 'type_format': '<I'},
			'rate': {'offset': 0x24, 'size': 4, 'type_format': '<I'},
			'sn76489_feedback': {
				'offset': 0x28,
				'size': 2,
				'type_format': '<H',
			},
			'sn76489_shift_register_width': {
				'offset': 0x2a,
				'size': 1,
				'type_format': 'B',
			},
			'ym2612_clock': {'offset': 0x2c, 'size': 4, 'type_format': '<I'},
			'ym2151_clock': {'offset': 0x30, 'size': 4, 'type_format': '<I'},
			'vgm_data_offset': {
				'offset': 0x34,
				'size': 4,
				'type_format': '<I',
			},
		},
		# Version 1.50`
		0x00000150: {
			'vgm_ident': {'offset': 0x00, 'size': 4, 'type_format': None},
			'eof_offset': {'offset': 0x04, 'size': 4, 'type_format': '<I'},
			'version': {'offset': 0x08, 'size': 4, 'type_format': '<I'},
			'sn76489_clock': {'offset': 0x0c, 'size': 4, 'type_format': '<I'},
			'ym2413_clock': {'offset': 0x10, 'size': 4, 'type_format': '<I'},
			'gd3_offset': {'offset': 0x14, 'size': 4, 'type_format': '<I'},
			'total_samples': {'offset': 0x18, 'size': 4, 'type_format': '<I'},
			'loop_offset': {'offset': 0x1c, 'size': 4, 'type_format': '<I'},
			'loop_samples': {'offset': 0x20, 'size': 4, 'type_format': '<I'},
			'rate': {'offset': 0x24, 'size': 4, 'type_format': '<I'},
			'sn76489_feedback': {
				'offset': 0x28,
				'size': 2,
				'type_format': '<H',
			},
			'sn76489_shift_register_width': {
				'offset': 0x2a,
				'size': 1,
				'type_format': 'B',
			},
			'ym2612_clock': {'offset': 0x2c, 'size': 4, 'type_format': '<I'},
			'ym2151_clock': {'offset': 0x30, 'size': 4, 'type_format': '<I'},
			'vgm_data_offset': {
				'offset': 0x34,
				'size': 4,
				'type_format': '<I',
			},
		},
		# SDM Hacked version number, we are happy enough to parse v1.51 as if it were 1.50 since the 1.51 updates dont apply to us anyway
		0x00000151: {
			'vgm_ident': {'offset': 0x00, 'size': 4, 'type_format': None},
			'eof_offset': {'offset': 0x04, 'size': 4, 'type_format': '<I'},
			'version': {'offset': 0x08, 'size': 4, 'type_format': '<I'},
			'sn76489_clock': {'offset': 0x0c, 'size': 4, 'type_format': '<I'},
			'ym2413_clock': {'offset': 0x10, 'size': 4, 'type_format': '<I'},
			'gd3_offset': {'offset': 0x14, 'size': 4, 'type_format': '<I'},
			'total_samples': {'offset': 0x18, 'size': 4, 'type_format': '<I'},
			'loop_offset': {'offset': 0x1c, 'size': 4, 'type_format': '<I'},
			'loop_samples': {'offset': 0x20, 'size': 4, 'type_format': '<I'},
			'rate': {'offset': 0x24, 'size': 4, 'type_format': '<I'},
			'sn76489_feedback': {
				'offset': 0x28,
				'size': 2,
				'type_format': '<H',
			},
			'sn76489_shift_register_width': {
				'offset': 0x2a,
				'size': 1,
				'type_format': 'B',
			},
			'ym2612_clock': {'offset': 0x2c, 'size': 4, 'type_format': '<I'},
			'ym2151_clock': {'offset': 0x30, 'size': 4, 'type_format': '<I'},
			'vgm_data_offset': {
				'offset': 0x34,
				'size': 4,
				'type_format': '<I',
			},
		},
		# SDM Hacked version number, we are happy enough to parse v1.60 as if it were 1.50 since the 1.51 updates dont apply to us anyway
		0x00000160: {
			'vgm_ident': {'offset': 0x00, 'size': 4, 'type_format': None},
			'eof_offset': {'offset': 0x04, 'size': 4, 'type_format': '<I'},
			'version': {'offset': 0x08, 'size': 4, 'type_format': '<I'},
			'sn76489_clock': {'offset': 0x0c, 'size': 4, 'type_format': '<I'},
			'ym2413_clock': {'offset': 0x10, 'size': 4, 'type_format': '<I'},
			'gd3_offset': {'offset': 0x14, 'size': 4, 'type_format': '<I'},
			'total_samples': {'offset': 0x18, 'size': 4, 'type_format': '<I'},
			'loop_offset': {'offset': 0x1c, 'size': 4, 'type_format': '<I'},
			'loop_samples': {'offset': 0x20, 'size': 4, 'type_format': '<I'},
			'rate': {'offset': 0x24, 'size': 4, 'type_format': '<I'},
			'sn76489_feedback': {
				'offset': 0x28,
				'size': 2,
				'type_format': '<H',
			},
			'sn76489_shift_register_width': {
				'offset': 0x2a,
				'size': 1,
				'type_format': 'B',
			},
			'ym2612_clock': {'offset': 0x2c, 'size': 4, 'type_format': '<I'},
			'ym2151_clock': {'offset': 0x30, 'size': 4, 'type_format': '<I'},
			'vgm_data_offset': {
				'offset': 0x34,
				'size': 4,
				'type_format': '<I',
			},
		}		
	}

	
	# constructor - pass in the filename of the VGM
	def __init__(self, vgm_filename):
	
		# open the vgm file and parse it
		vgm_file = open(vgm_filename, 'rb')
		vgm_data = vgm_file.read()
		
		# Store the VGM data and validate it
		self.data = ByteBuffer(vgm_data)
		
		vgm_file.close()
		
		# parse
		self.validate_vgm_data()

		# Set up the variables that will be populated
		self.command_list = []
		self.data_block = None
		self.gd3_data = {}
		self.metadata = {}

		# Parse the VGM metadata and validate the VGM version
		self.parse_metadata()
		
		print self.metadata
		print "Version " + "%x" % int(self.metadata['version'])
		
		self.validate_vgm_version()
		
		# see if this VGM uses Dual Chip mode
		if (self.metadata['sn76489_clock'] & 0x40000000) == 0x40000000:
			self.dual_chip_mode_enabled = True
		else:
			self.dual_chip_mode_enabled = False
			
		print "VGM Dual Chip Mode=" + str(self.dual_chip_mode_enabled)
		

		# override/disable dual chip commands in the output stream if required
		if (self.disable_dual_chip == True) and (self.dual_chip_mode_enabled == True) :
			# remove the clock flag that enables dual chip mode
			self.metadata['sn76489_clock'] = self.metadata['sn76489_clock'] & 0xbfffffff
			self.dual_chip_mode_enabled = False
			print "Dual Chip Mode Disabled - DC Commands will be removed"

		# take a copy of the clock speed for this VGM
		self.vgm_source_clock = self.metadata['sn76489_clock']

		# force beeb mode
		if FORCE_BBC_MODE == True:
			self.metadata['sn76489_feedback'] = 0x0003	# 0x0006 for	SN76494, SN76496
			self.metadata['sn76489_clock'] = 0x003d0900	# 4Mhz on Beeb, usually 3.579545MHz (NTSC) for Sega-based PSG tunes
			self.metadata['sn76489_shift_register_width'] = 15	# 16 for Sega
		
		
		self.vgm_target_clock = self.metadata['sn76489_clock']
		
		# Parse GD3 data and the VGM commands
		self.parse_gd3()
		self.parse_commands()

	def validate_vgm_data(self):
		# Save the current position of the VGM data
		original_pos = self.data.tell()

		# Seek to the start of the file
		self.data.seek(0)

		# Perform basic validation on the given file by checking for the VGM
		# magic number ('Vgm ')
		if self.data.read(4) != self.vgm_magic_number:
			# Could not find the magic number. The file could be gzipped (e.g.
			# a vgz file). Try un-gzipping the file and trying again.
			self.data.seek(0)
			self.data = gzip.GzipFile(fileobj=self.data, mode='rb')

			try:
				if self.data.read(4) != self.vgm_magic_number:
					raise ValueError('Data does not appear to be a valid VGM file')
			except IOError:
				# IOError will be raised if the file is not a valid gzip file
				raise ValueError('Data does not appear to be a valid VGM file')

		# Seek back to the original position in the VGM data
		self.data.seek(original_pos)
		
	def parse_metadata(self):
		# Save the current position of the VGM data
		original_pos = self.data.tell()

		# Create the list to store the VGM metadata
		self.metadata = {}

		# Iterate over the offsets and parse the metadata
		for version, offsets in self.metadata_offsets.items():
			for value, offset_data in offsets.items():

				# Seek to the data location and read the data
				self.data.seek(offset_data['offset'])
				data = self.data.read(offset_data['size'])

				# Unpack the data if required
				if offset_data['type_format'] is not None:
					self.metadata[value] = struct.unpack(
						offset_data['type_format'],
						data,
					)[0]
				else:
					self.metadata[value] = data

		# Seek back to the original position in the VGM data
		self.data.seek(original_pos)

	def validate_vgm_version(self):
		if self.metadata['version'] not in self.supported_ver_list:
			print "VGM version is not supported"
			raise VersionError('VGM version is not supported')

	def parse_gd3(self):
		# Save the current position of the VGM data
		original_pos = self.data.tell()

		# Seek to the start of the GD3 data
		self.data.seek(
			self.metadata['gd3_offset'] +
			self.metadata_offsets[self.metadata['version']]['gd3_offset']['offset']
		)

		# Skip 8 bytes ('Gd3 ' string and 4 byte version identifier)
		self.data.seek(8, 1)

		# Get the length of the GD3 data, then read it
		gd3_length = struct.unpack('<I', self.data.read(4))[0]
		gd3_data = ByteBuffer(self.data.read(gd3_length))

		# Parse the GD3 data
		gd3_fields = []
		current_field = b''
		while True:
			# Read two bytes. All characters (English and Japanese) in the GD3
			# data use two byte encoding
			char = gd3_data.read(2)

			# Break if we are at the end of the GD3 data
			if char == b'':
				break

			# Check if we are at the end of a field, if not then continue to
			# append to "current_field"
			if char == b'\x00\x00':
				gd3_fields.append(current_field)
				current_field = b''
			else:
				current_field += char

		# Once all the fields have been parsed, create a dict with the data
		self.gd3_data = {
			'title_eng': gd3_fields[0],
			'title_jap': gd3_fields[1],
			'game_eng': gd3_fields[2],
			'game_jap': gd3_fields[3],
			'console_eng': gd3_fields[4],
			'console_jap': gd3_fields[5],
			'artist_eng': gd3_fields[6],
			'artist_jap': gd3_fields[7],
			'date': gd3_fields[8],
			'vgm_creator': gd3_fields[9],
			'notes': gd3_fields[10],
		}

		# Seek back to the original position in the VGM data
		self.data.seek(original_pos)

	def parse_commands(self):
		# Save the current position of the VGM data
		original_pos = self.data.tell()

		# Seek to the start of the VGM data
		self.data.seek(
			self.metadata['vgm_data_offset'] +
			self.metadata_offsets[self.metadata['version']]['vgm_data_offset']['offset']
		)

		while True:
			# Read a byte, this will be a VGM command, we will then make
			# decisions based on the given command
			command = self.data.read(1)

			# Break if we are at the end of the file
			if command == '':
				break

			# 0x4f dd - Game Gear PSG stereo, write dd to port 0x06
			# 0x50 dd - PSG (SN76489/SN76496) write value dd
			if command in [b'\x4f', b'\x50']:
				self.command_list.append({
					'command': command,
					'data': self.data.read(1),
				})

			# 0x51 aa dd - YM2413, write value dd to register aa
			# 0x52 aa dd - YM2612 port 0, write value dd to register aa
			# 0x53 aa dd - YM2612 port 1, write value dd to register aa
			# 0x54 aa dd - YM2151, write value dd to register aa
			elif command in [b'\x51', b'\x52', b'\x53', b'\x54']:
				self.command_list.append({
					'command': command,
					'data': self.data.read(2),
				})

			# 0x61 nn nn - Wait n samples, n can range from 0 to 65535
			elif command == b'\x61':
				self.command_list.append({
					'command': command,
					'data': self.data.read(2),
				})

			# 0x62 - Wait 735 samples (60th of a second)
			# 0x63 - Wait 882 samples (50th of a second)
			# 0x66 - End of sound data
			elif command in [b'\x62', b'\x63', b'\x66']:
				self.command_list.append({'command': command, 'data': None})

				# Stop processing commands if we are at the end of the music
				# data
				if command == b'\x66':
					break

			# 0x67 0x66 tt ss ss ss ss - Data block
			elif command == b'\x67':
				# Skip the compatibility and type bytes (0x66 tt)
				self.data.seek(2, 1)

				# Read the size of the data block
				data_block_size = struct.unpack('<I', self.data.read(4))[0]

				# Store the data block for later use
				self.data_block = ByteBuffer(self.data.read(data_block_size))

			# 0x7n - Wait n+1 samples, n can range from 0 to 15
			# 0x8n - YM2612 port 0 address 2A write from the data bank, then
			#        wait n samples; n can range from 0 to 15
			elif b'\x70' <= command <= b'\x8f':
				self.command_list.append({'command': command, 'data': None})

			# 0xe0 dddddddd - Seek to offset dddddddd (Intel byte order) in PCM
			#                 data bank
			elif command == b'\xe0':
				self.command_list.append({
					'command': command,
					'data': self.data.read(4),
				})
				
			# 0x30 dd - dual chip command
			elif command == b'\x30':
				if self.dual_chip_mode_enabled:
					self.command_list.append({
						'command': command,
						'data': self.data.read(1),
					})
			

		# Seek back to the original position in the VGM data
		self.data.seek(original_pos)
		
		

			
			
	def write_vgm(self, filename):
	
		vgm_stream = bytearray()

		# convert the VGM command list to a byte array
		for elem in self.command_list:
			command = elem['command']
			data = elem['data']
			
			if (data != None):
				print "command=" + str(binascii.hexlify(command)) + ", data=" + str(binascii.hexlify(data))
				
			# filter dual chip
			if b'\x30' == command:
				print "DUAL CHIP COMMAND"
				#continue
				#command = b'\x50'

			
			vgm_stream.extend(command)
			if (data != None):
				vgm_stream.extend(data)
		
		# build the GD3 data block
		gd3_data = bytearray()
		gd3_data.extend(self.gd3_data['title_eng'] + b'\x00\x00')
		gd3_data.extend(self.gd3_data['title_jap'] + b'\x00\x00')
		gd3_data.extend(self.gd3_data['game_eng'] + b'\x00\x00')
		gd3_data.extend(self.gd3_data['game_jap'] + b'\x00\x00')
		gd3_data.extend(self.gd3_data['console_eng'] + b'\x00\x00')
		gd3_data.extend(self.gd3_data['console_jap'] + b'\x00\x00')
		gd3_data.extend(self.gd3_data['artist_eng'] + b'\x00\x00')
		gd3_data.extend(self.gd3_data['artist_jap'] + b'\x00\x00')
		gd3_data.extend(self.gd3_data['date'] + b'\x00\x00')
		gd3_data.extend(self.gd3_data['vgm_creator'] + b'\x00\x00')
		gd3_data.extend(self.gd3_data['notes'] + b'\x00\x00')
		
		gd3_stream = bytearray()
		gd3_stream.extend('Gd3 ')
		gd3_stream.extend(struct.pack('I', 0x100))				# GD3 version
		gd3_stream.extend(struct.pack('I', len(gd3_data)))		# GD3 length		
		gd3_stream.extend(gd3_data)

		# build the full VGM stream
		vgm_stream_length = len(vgm_stream)
		bg3_stream_length = len(gd3_stream)
		print bg3_stream_length
		
		vgm_data = bytearray()
		vgm_data.extend(self.vgm_magic_number)
		vgm_data.extend(struct.pack('I', 64 + vgm_stream_length + bg3_stream_length - 4))				# EoF offset
		vgm_data.extend(struct.pack('I', 0x00000151))		# Version
		vgm_data.extend(struct.pack('I', self.metadata['sn76489_clock']))
		vgm_data.extend(struct.pack('I', self.metadata['ym2413_clock']))
		vgm_data.extend(struct.pack('I', (64-20) + vgm_stream_length))				# GD3 offset
		vgm_data.extend(struct.pack('I', self.metadata['total_samples']))				# total samples
		vgm_data.extend(struct.pack('I', 0)) #self.metadata['loop_offset']))				# loop offset
		vgm_data.extend(struct.pack('I', 0)) #self.metadata['loop_samples']))				# loop # samples
		vgm_data.extend(struct.pack('I', self.metadata['rate']))				# rate
		vgm_data.extend(struct.pack('H', self.metadata['sn76489_feedback']))				# sn fb
		vgm_data.extend(struct.pack('B', self.metadata['sn76489_shift_register_width']))				# SNW	
		vgm_data.extend(struct.pack('B', 0))				# SN Flags			
		vgm_data.extend(struct.pack('I', self.metadata['ym2612_clock']))		
		vgm_data.extend(struct.pack('I', self.metadata['ym2151_clock']))	
		vgm_data.extend(struct.pack('I', 12))				# VGM data offset
		vgm_data.extend(struct.pack('I', 0))				# SEGA PCM clock	
		vgm_data.extend(struct.pack('I', 0))				# SPCM interface	

		# attach the vgm data stream
		vgm_data.extend(vgm_stream)

		# attach the vgm gd3 block
		vgm_data.extend(gd3_stream)
		

			
			
		
		print self.metadata
		
		vgm_file = open(filename, 'wb')
		vgm_file.write(vgm_data)
		vgm_file.close()
		
	
#-------------------------------------------------------------------------------------------------




vgm_data = VgmStream(filename)
print vgm_data.metadata
print vgm_data.gd3_data

# total number of commands in the vgm stream
num_commands = len(vgm_data.command_list)

# total number of samples in the vgm stream
total_samples = int(vgm_data.metadata['total_samples'])






# VGM commands:
# 0x50	[dd]	= PSG SN76489 write value dd
# 0x61	[nnnn]	= WAIT n cycles (0-65535)
# 0x62			= WAIT 735 samples (1/60 sec)
# 0x63			= WAIT 882 samples (1/50 sec)
# 0x66			= END
# 0x7n			= WAIT n+1 samples (0-15)

#--------------------------------------------------------------------------------------------------------------------------------
# SN76489 register writes
# If bit 7 is 1 then the byte is a LATCH/DATA byte.
#  %1cctdddd
#	cc - channel (0-3)
#	t - type (1 to latch volume, 1 to latch tone/noise)
#	dddd - placed into the low 4 bits of the relevant register. For the three-bit noise register, the highest bit is discarded.
#
# If bit 7 is 0 then the byte is a DATA byte.
#  %0-DDDDDD
# If the currently latched register is a tone register then the low 6 bits of the byte (DDDDDD) 
#	are placed into the high 6 bits of the latched register. If the latched register is less than 6 bits wide 
#	(ie. not one of the tone registers), instead the low bits are placed into the corresponding bits of the 
#	register, and any extra high bits are discarded.
#
# Tone registers
#	DDDDDDdddd = cccccccccc
#	DDDDDDdddd gives the 10-bit half-wave counter reset value.
#
# Volume registers
#	(DDDDDD)dddd = (--vvvv)vvvv
#	dddd gives the 4-bit volume value.
#	If a data byte is written, the low 4 bits of DDDDDD update the 4-bit volume value. However, this is unnecessary.
#
# Noise register
#	(DDDDDD)dddd = (---trr)-trr
#	The low 2 bits of dddd select the shift rate and the next highest bit (bit 2) selects the mode (white (1) or "periodic" (0)).
#	If a data byte is written, its low 3 bits update the shift rate and mode in the same way.
#--------------------------------------------------------------------------------------------------------------------------------

vgm_time = 0
playback_time = 0


vgm_command_index = 0

unhandled_commands = 0


# first step is to quantize the command stream to the playback rate rather than the sample rate

output_command_list = []

if True:

	# used by the clock retuning code, initialized once at the start of the song, so that latched register states are preserved across the song
	latched_tone_frequencies = [0, 0, 0, 0]
	latched_volumes = [0, 0, 0, 0]
	latched_channel = 0
					
	accumulated_time = 0
	latched_channel = 0
	# process the entire vgm
	while playback_time < total_samples:

		quantized_command_list = []
		playback_time += vgm_frequency/play_frequency
		
		# if playback time has caught up with vgm_time, process the commands
		while vgm_time <= playback_time and vgm_command_index < len(vgm_data.command_list): 
		
			# fetch next command & associated data
			command = vgm_data.command_list[vgm_command_index]["command"]
			data = vgm_data.command_list[vgm_command_index]["data"]
			
			# process the command
			# writes get accumulated in this time slot
			# waits get accumulated to vgm_time
			
			if b'\x70' <= command <= b'\x7f':	
				pdata = binascii.hexlify(command)
				t = int(pdata, 16)
				t &= 15
				t += 1
				vgm_time += t
				scommand = "WAITn"
				print "WAITN=" + str(t)
			else:
				pcommand = binascii.hexlify(command)
			
				if pcommand == "50":
					scommand = "WRITE"

					pdata = binascii.hexlify(data)
					w = int(pdata, 16)	



					
					# OPTIMIZATION - see if the new register write supersedes a previous one, and remove redundant earlier writes
					if (OPTIMIZE_COMMANDS == True):
						if (len(quantized_command_list) > 0):					
							# first check for volume writes as these are easier

							
							

							# Check if LATCH/DATA write enabled - since this is the start of a write command
							if w & 128:
								# Get channel id
								channel = (w>>5)&3

								# Check if VOLUME flag set
								if (w & 16):
									# scan previous commands to see if same channel volume has been set
									# if so, remove the previous one
									temp_command_list = []
									for c in quantized_command_list:
										qdata = c["data"]
										qw = int(binascii.hexlify(qdata), 16)
										redundant = False
										
										# Check if LATCH/DATA write enabled 
										if qw & 128:
									
										
											# Check if VOLUME flag set
											if (qw & 16):
												# Get channel id
												qchannel = (qw>>5)&3
												if (qchannel == channel):
													redundant = True
										
										# we cant remove the item directly from quantized_command_list since we are iterating through it
										# so we build a second optimized list
										if (not redundant):
											temp_command_list.append(c)
										else:
											print "Removed redundant volume write"
											
										# replace command list with optimized command list
										quantized_command_list = temp_command_list
								
								else:
									# process tones, these are a bit more complex, since they might comprise two commands
									
									# scan previous commands to see if a tone has been previously set on the same channel
									# if so, remove the previous one
									temp_command_list = []
									redundant_tone_data = False	# set to true if 
									for c in quantized_command_list:
										qdata = c["data"]
										qw = int(binascii.hexlify(qdata), 16)
	
										redundant = False
										
										# if a previous tone command was removed as redundant, any subsequent non-latch tone writes are also redundant
										if (redundant_tone_data == True):
											redundant_tone_data = False
											if (qw & 128) == 0:	# detect non latched data write
												redundant = True
										else:
											# Check if LATCH/DATA write enabled 
											if qw & 128:
											
												# Check if VOLUME flag NOT set (ie. TONE)
												if (qw & 16) == 0:
													# Get channel id
													qchannel = (qw>>5)&3
													if (qchannel == channel):
														redundant = True
														redundant_tone_data = True	# indicate that if next command is a non-latched tone data write, it too is redundant
										
										# we cant remove the item directly from quantized_command_list since we are iterating through it
										# so we build a second optimized list
										if (not redundant):
											temp_command_list.append(c)
										else:
											print "Removed redundant tone write"
											
										# replace command list with optimized command list
										quantized_command_list = temp_command_list							
					
					# add the latest command to the list
					
					# Apply channel filtering if required
					if w & 128:
						# Get channel id
						latched_channel = (w>>5)&3
						
					filtered = False
					if latched_channel == 0 and FILTER_CHANNEL0 == True:
						filtered = True
					if latched_channel == 1 and FILTER_CHANNEL1 == True:
						filtered = True
					if latched_channel == 2 and FILTER_CHANNEL2 == True:
						filtered = True
					if latched_channel == 3 and FILTER_CHANNEL3 == True:
						filtered = True
					
					if filtered == False:
						quantized_command_list.append( { 'command' : command, 'data' : data } )
				else:
					if pcommand == "61":
						scommand = "WAIT"
						pdata = binascii.hexlify(data)
						t = int(pdata, 16)
						# sdm: swap bytes to LSB
						lsb = t & 255
						msb = (t / 256)
						t = (lsb * 256) + msb
						vgm_time += t		
						print "WAIT=" + str(t)
					else:			
						if pcommand == "66":
							scommand = "END"
							# send the end command
							output_command_list.append( { 'command' : command, 'data' : data } )
							# end
						else:
							if pcommand == "62":
								scommand = "WAIT60"
								vgm_time += 735
							else:
								if pcommand == "63":
									scommand = "WAIT50"
									vgm_time += 882								
								else:
									scommand = "UNKNOWN"
									unhandled_commands += 1		
			
			print "vgm_time=" + str(vgm_time) + ", playback_time=" + str(playback_time) + ", vgm_command_index=" + str(vgm_command_index) + ", output_command_list=" + str(len(output_command_list)) + ", command=" + scommand
			vgm_command_index += 1
		
		print "vgm_time has caught up with playback_time"
		

		
		# we've caught up with playback time, so append the quantized command list to the output command list
		if (len(quantized_command_list) > 0) :
		
			# re-tune any tone commands if target clock is different to source clock
			# i think it's safe to do this in the quantized packets we've created, as they tend to be completed within a single time slot
			# (eg. little or no chance of a multi-tone LATCH+DATA write being split by a wait command)
			if ENABLE_RETUNE == True:
				if (vgm_data.vgm_source_clock != vgm_data.vgm_target_clock):
				
					# iterate through write commands looking for tone writes and recalculate their frequencies

					for n in range(len(quantized_command_list)):
						qdata = quantized_command_list[n]["data"]
						
						# Check if LATCH/DATA write 								
						qw = int(binascii.hexlify(qdata), 16)
						if qw & 128:
						
							# low tone values are high frequency (min 0x001)
							# high tone values are low frequence (max 0x3ff)
							
							# Get channel id and latch it
							latched_channel = (qw>>5)&3
								
							# Check if TONE						
							if (qw & 16) == 0:
							

							
								# get low 4 bits and merge with latched channel's frequency register
								qfreq = (qw & 0b00001111)
								latched_tone_frequencies[latched_channel] = (latched_tone_frequencies[latched_channel] & 0b1111110000) | qfreq
								
								# look ahead, and see if the next command is a DATA write as if so, this will be part of the same tone commmand
								# so load this into our register as well so that we have the correct tone frequency to work with
								multi_write = False
								if n < (len(quantized_command_list)-1): # check we dont overflow the array

									ndata = quantized_command_list[n+1]["data"]

									# Check if next command is a DATA write 								
									nw = int(binascii.hexlify(ndata), 16)
									if (nw & 128) == 0:
										multi_write = True
										nfreq = (nw & 0b00111111)
										latched_tone_frequencies[latched_channel] = (latched_tone_frequencies[latched_channel] & 0b0000001111) | nfreq << 4										
																								
								# compute the correct frequency
								# first check it is not 0 (illegal value)
								new_freq = 0
								if latched_tone_frequencies[latched_channel] > 0:
								
									if True:
										# compute frequency of current tone
										hz = float(vgm_data.vgm_source_clock) / ( 2.0 * float(latched_tone_frequencies[latched_channel]) * 16.0)
										#clock_ratio = float(vgm_data.vgm_source_clock) / float(vgm_data.vgm_target_clock)

										tune_ratio = 1.0
										if RETUNE_PERIODIC == True:	
											# to use the periodic noise effect as a bass line, it uses the tone on channel 2 to drive PN frequency on channel 3
											# typically tracks that use this effect will disable the volume of channel 2
											# we detect this case and detune channel 2 tone by a further 6.25% to fix the tuning
											if latched_channel == 2 and latched_volumes[2] == 15:	
											
												if True:
													noise_ratio = (15.0 / 16.0) * (float(vgm_data.vgm_source_clock) / float(vgm_data.vgm_target_clock))
													print "noise_ratio=" + str(noise_ratio)
													v = float(latched_tone_frequencies[latched_channel]) / noise_ratio
													print "original freq=" + str(latched_tone_frequencies[latched_channel]) + ", new freq=" + str(v)
													#tune_ratio = 1.0/noise_ratio #hz /= noise_ratio
												else:
													noise_hz_source = float(vgm_data.vgm_source_clock) / ( 2.0 * float(latched_tone_frequencies[2]) * 16.0 * 16.0)
													print "noise_hz_source=" + str(noise_hz_source) + ", v_source=" + str(latched_tone_frequencies[2])
													# calculate how to generate the same frequency on the new clockrate
													v = float(vgm_data.vgm_target_clock) / (2.0 * noise_hz_source * 16.0 * 15.0)
													hz = float(vgm_data.vgm_target_clock) / ( 2.0 * v * 16.0)
													noise_hz_target = float(vgm_data.vgm_target_clock) / ( 2.0 * v * 16.0 * 15.0)
													print "noise_hz_target=" + str(hz) + ", v_target=" + str(v) + ", noise_hz_target=" + str(noise_hz_target)
													
													# let calc below convert new hz to a value
													#noise_hz_target = float(vgm_data.vgm_target_clock) / ( 2.0 * float(latched_tone_frequencies[2]) * 16.0 * 15.0)
													#noise_ratio = noise_hz_source / noise_hz_target
													
													#print "noise_ratio=" + str(noise_ratio)
											
													#hz = (hz * clock_ratio) / 1.0625 # - hz*0.0625 # detune by 1/15 to compensate for shorter shift register (15bits instead of 16)
													#tune_ratio = (1.0 + (1.0 - 15.0/16.0)) * (1.0 + (1.0 - clock_ratio)) #(1 + 0.0625*0.5) #* clock_ratio
													#hz = hz * noise_ratio #/ 16.0 #1.0625 #- hz * 0.0625

												
												print "detuned channel 2 with zero volume by 6.25%"										

											else:
										
										
												# compute register value for generating the same frequency using the target chip's clock rate
												print "hz=" + str(hz)
												v = float(vgm_data.vgm_target_clock) / (2.0 * hz * 16.0 )
												#v *= tune_ratio
												print "v=" + str(v)
										else:
											# compute register value for generating the same frequency using the target chip's clock rate
											print "hz=" + str(hz)
											v = float(vgm_data.vgm_target_clock) / (2.0 * hz * 16.0 )
											#v *= tune_ratio
											print "v=" + str(v)										
										
										
										# due to the integer maths, some precision is lost at the lower end
										new_freq = int(round(v)) #int(math.ceil(v))
										
									else:								
										new_freq = (long(latched_tone_frequencies[latched_channel]) * long(vgm_data.vgm_target_clock) + long(vgm_data.vgm_source_clock/2)) / long(vgm_data.vgm_source_clock)
									
									# leave channel 3 (noise channel) alone.. it's not a frequency
									if latched_channel == 3:
										new_freq = latched_tone_frequencies[latched_channel]
										
									if False: #RETUNE_PERIODIC == True:
										# to use the periodic noise effect as a bass line, it uses the tone on channel 2 to drive PN frequency on channel 3
										# typically tracks that use this effect will disable the volume of channel 2
										# we detect this case and detune channel 2 tone by a further 6.25% to fix the tuning
										if latched_channel == 2 and latched_volumes[2] == 15:
											new_freq = int( float(new_freq) * (1.0625) )	# detune by 1/15 to compensate for shorter shift register (15bits instead of 16)
											print "detuned channel 2 with zero volume by 6.25%"
										
									
									hz1 = float(vgm_data.vgm_source_clock) / (2.0 * float(latched_tone_frequencies[latched_channel]) * 16.0) # target frequency
									hz2 = float(vgm_data.vgm_target_clock) / (2.0 * float(new_freq) * 16.0)
									print "channel=" + str(latched_channel) + ", old frequency=" + str(latched_tone_frequencies[latched_channel]) + ", new frequency=" + str(new_freq) + ", source_clock=" + str(vgm_data.vgm_source_clock) + ", target_clock=" + str(vgm_data.vgm_target_clock) + ", src_hz=" + str(hz1) + ", tgt_hz=" + str(hz2)
								else:
									print "Zero frequency tone detected on channel " + str(latched_channel)
									
								# write back the command(s) with the correct frequency
								lo_data = (qw & 0b11110000) | (new_freq & 0b00001111)
								quantized_command_list[n]["data"] = struct.pack('B', lo_data)
								
								hi_data = -1
								if multi_write == True:
									hi_data = (new_freq>>4) & 0b00111111
									quantized_command_list[n+1]["data"] = struct.pack('B', hi_data)	
								else:
									print "SINGLE REGISTER TONE WRITE on CHANNEL " + str(latched_channel)

								print "new_freq=" + format(new_freq, 'x') + ", lo_data=" + format(lo_data, '02x') + ", hi_data=" + format(hi_data, '02x')
							else:
								# track volumes so we can apply the periodic noise retune if necessary
								
								# hack to force channel 2 volume high (so we can test periodic noise channel tuning)
								#if latched_channel == 2:
								#	qw = qw & 0xf0
								#	quantized_command_list[n]["data"] = struct.pack('B', qw)
									
								latched_volumes[latched_channel] = qw & 15

							
							
		
			
			
		
			# flush any pending wait commands before data writes, to optimize redundant wait commands

			print "Flushing " + str(len(quantized_command_list)) + " commands, accumulated_time=" + str(accumulated_time)
			while (accumulated_time > 0):
				
				# ensure no wait commands exceed the 16-bit limit
				t = accumulated_time
				if (t > 65535):
					t = 65535
				
				# optimization: if quantization time step is 1/50 or 1/60 of a second use the single byte wait
				if t == 882: # 50Hz
					print "Outputting WAIT50"
					output_command_list.append( { 'command' : b'\x63', 'data' : None } )	
				else:
					if t == 735: # 60Hz
						output_command_list.append( { 'command' : b'\x62', 'data' : None } )	
					else:
						# else emit the full 16-bit wait command (3 bytes)
						output_command_list.append( { 'command' : b'\x61', 'data' : struct.pack('H', t) } )	

				accumulated_time -= t
					
			# output pending commands
			output_command_list += quantized_command_list


		# accumulate time to next quantized time period
		next_w = (vgm_frequency/play_frequency)
		accumulated_time += next_w
		print "next_w=" + str(next_w)


	# report
	print "Processed VGM stream, resampled to " + str(play_frequency) + "Hz" 
	print "- originally contained " + str(num_commands) + " commands, now contains " + str(len(output_command_list)) + " commands"

	vgm_data.command_list = output_command_list
	num_commands = len(output_command_list)

# now we've quantized we can eliminate redundant register writes
# for each tone channel
#  only store the last write
# for each volume channel
#  only store the last write
# maybe incorporate this into the quantization	
	
	
	
	
	
	
	
	
	
	
	
# analysis / output

minwait = 99999
minwaitn = 99999
writecount = 0
totalwritecount = 0
maxwritecount = 0
writedictionary = []
waitdictionary = []
tonedictionary = []
maxtonedata = 0
numtonedatawrites = 0
unhandledcommands = 0
totaltonewrites = 0
totalvolwrites = 0
latchtone = 0

# convert to event sequence, one event per channel, with tones & volumes changed

#event = { "wait" : 0, "t0" : -1, "v0" : -1, "t1" : -1, "v1" : -1, "t2" : -1, "v2" : -1, "t3" : -1,  "v3" : - 1 }
event = None

#nnnnnn tttttt vv ttttt vv tttt vv ttttt vvv

eventlist = []

waittime = 0
tonechannel = 0

for n in range(num_commands):
	command = vgm_data.command_list[n]["command"]
	data = vgm_data.command_list[n]["data"]
	pdata = "NONE"
	
	# process command
	if b'\x70' <= command <= b'\x7f':		
		pcommand = "WAITn"
	else:
		pcommand = binascii.hexlify(command)
		
	
		if pcommand == "50":
			pcommand = "WRITE"	
			# count number of serial writes
			writecount += 1
			totalwritecount += 1
			if data not in writedictionary:
				writedictionary.append(data)
		else:
			if writecount > maxwritecount:
				maxwritecount = writecount
			writecount = 0
			if pcommand == "61":
				pcommand = "WAIT "
			else:			
				if pcommand == "66":
					pcommand = "END"
				else:
					if pcommand == "62":
						pcommand = "WAIT60"
					else:
						if pcommand == "63":
							pcommand = "WAIT50"						
						else:
							unhandledcommands += 1
							pdata = "UNKNOWN COMMAND"
							
		



	# process data
	# handle data writes first	
	if pcommand == "WRITE":
	
		# flush any pending wait events
		if waittime > 0:
			# create a new event object, serial writes will be added to this single object
			event = { "wait" : waittime, "t0" : -1, "v0" : -1, "t1" : -1, "v1" : -1, "t2" : -1, "v2" : -1, "t3" : -1,  "v3" : - 1 }	
			eventlist.append(event)
			waittime = 0
			event = None
		
		if event == None:
			event = { "wait" : 0, "t0" : -1, "v0" : -1, "t1" : -1, "v1" : -1, "t2" : -1, "v2" : -1, "t3" : -1,  "v3" : - 1 }	
			
		# process the write data
		pdata = binascii.hexlify(data)
		w = int(pdata, 16)
		s = pdata
		pdata = s + " (" + str(w) + ")"
		if w & 128:
			tonechannel = (w&96)>>5
			pdata += " LATCH"
			pdata += " CH" + str(tonechannel)
			
			if (w & 16):
				pdata += " VOL"
				totalvolwrites += 1
				vol = w & 15
				if tonechannel == 0:
					event["v0"] = vol
				if tonechannel == 1:
					event["v1"] = vol
				if tonechannel == 2:
					event["v2"] = vol
				if tonechannel == 3:
					event["v3"] = vol
					
				
			else:
				pdata += " TONE"
				totaltonewrites += 1
				latchtone = w & 15
			pdata += " " + str(w & 15)
		else:
			pdata += " DATA"
			numtonedatawrites += 1
			if w > maxtonedata:
				maxtonedata = w
			tone = latchtone + (w << 4)
			pdata += " " + str(w) + " (tone=" + str(tone) + ")"
			
			latchtone = 0
			if tone not in tonedictionary:
				tonedictionary.append(tone)
			
			if tonechannel == 0:
				event["t0"] = tone
			if tonechannel == 1:
				event["t1"] = tone
			if tonechannel == 2:
				event["t2"] = tone
			if tonechannel == 3:
				event["t3"] = tone
	else:
		# process wait or end commands
		
		# flush any previously gathered write event
		if event != None:
			eventlist.append(event)
			event = None	
			
		if pcommand == "WAIT60":			
			t = 735
			waittime += t
			if t not in waitdictionary:
				waitdictionary.append(t)

		if pcommand == "WAIT50":
			t = 882
			waittime += t
			if t not in waitdictionary:
				waitdictionary.append(t)	

		if pcommand == "WAIT ":
			pdata = binascii.hexlify(data)
			t = int(pdata, 16)
			# sdm: swap bytes to LSB
			lsb = t & 255
			msb = (t / 256)
			t = (lsb * 256) + msb
			waittime += t
			if t < minwait:
				minwait = t
			ms = t * 1000 / 44100
			pdata = str(ms) +"ms, " + str(t) + " samples (" + pdata +")"
			if t not in waitdictionary:
				waitdictionary.append(t)					


		if pcommand == "WAITn":
			# data will be "None" for this but thats ok.
			pdata = binascii.hexlify(command)
			t = int(pdata, 16)
			t &= 15
			waittime += t
			if t < minwaitn:
				minwaitn = t
			ms = t * 1000 / 44100
			pdata = str(ms) +"ms, " + str(t) + " samples (" + pdata +")"
			if t not in waitdictionary:
				waitdictionary.append(t)

		
		

		

	print "#" + str(n) + " Command:" + pcommand + " Data:" + pdata # '{:02x}'.format(data)

# NOTE: multiple register writes happen instantaneously
# ideas:
# quantize tone from 10-bit to 8-bit? Doubt it would sound the same.
# doesn't seem to be many tone changes, and tones are few in range (i bet vibrato and arpeggios change this though)
# volume is the main variable - possibly separate the volume stream and resample it?
# volume can be changed using one byte
# tone requires two bytes and could be quantized to larger time steps?
 

totalwaitcommands = num_commands - totalwritecount
clockspeed = 2000000
samplerate = 44100
cyclespersample = clockspeed/samplerate


#--------------------------------
print "--------------------------------------------------------------------------"
print "Number of sampled events: " + str(len(eventlist))

for n in range(len(eventlist)):
	event = eventlist[n]
	print "%6d" % n + " " + str(event)
	

print "--------------------------------------------------------------------------"

# compile volume channel 0 stream

eventlist_v0 = []
eventlist_v1 = []
eventlist_v2 = []
eventlist_v3 = []

eventlist_t0 = []
eventlist_t1 = []
eventlist_t2 = []
eventlist_t3 = []

def printEvents(eventlistarray, arrayname):
	print ""
	print "Total " + arrayname + " events: " + str(len(eventlistarray))
	for n in range(len(eventlistarray)):
		event = eventlistarray[n]
		print "%6d" % n + " " + str(event)

def processEvents(eventsarray_in, eventsarray_out, tag_in, tag_out):
	waittime = 0
	for n in range(len(eventsarray_in)):
		event = eventsarray_in[n]
		t = event["wait"]
		if t > 0:
			waittime += t
		else:
			v = event[tag_in]
			if v > -1:
				eventsarray_out.append({ "wait" : waittime, tag_out : v })
				waittime = 0
				
	printEvents(eventsarray_out, tag_in)

processEvents(eventlist, eventlist_v0, "v0", "v")
processEvents(eventlist, eventlist_v1, "v1", "v")
processEvents(eventlist, eventlist_v2, "v2", "v")
processEvents(eventlist, eventlist_v3, "v3", "v")

processEvents(eventlist, eventlist_t0, "t0", "t")
processEvents(eventlist, eventlist_t1, "t1", "t")
processEvents(eventlist, eventlist_t2, "t2", "t")
processEvents(eventlist, eventlist_t3, "t3", "t")				


# ----------------------- analysis


print "Number of commands in data file: " + str(num_commands)
print "Total samples in data file: " + str(total_samples) + " (" + str(total_samples*1000/44100) + " ms)"
print "Smallest wait time was: " + str(minwait) + " samples"
print "Smallest waitN time was: " + str(minwaitn) + " samples"
print "ClockSpeed:" + str(clockspeed) + " SampleRate:" + str(samplerate) + " CyclesPerSample:" + str(cyclespersample) + " CyclesPerWrite:" + str(cyclespersample*minwait)
print "Updates Per Second:" + str(clockspeed/(cyclespersample*minwait))
print "Total register writes:" + str(totalwritecount) + " Max Sequential Writes:" + str(maxwritecount) # sequential writes happen at same time, in series
print "Total tone writes:" + str(totaltonewrites)
print "Total vol writes:" + str(totalvolwrites)
print "Total wait commands:" + str(totalwaitcommands)
print "Write dictionary contains " + str(len(writedictionary)) + " unique entries"
print "Wait dictionary contains " + str(len(waitdictionary)) + " unique entries"
print "Tone dictionary contains " + str(len(tonedictionary)) + " unique entries"
print "Largest Tone Data Write value was " + str(maxtonedata)
print "Number of Tone Data writes was " + str(numtonedatawrites)
print "Number of unhandled commands was " + str(unhandledcommands)


estimatedfilesize = totalwritecount + totalwaitcommands

print "Estimated file size is " + str(estimatedfilesize) + " bytes, assuming 1 byte per command can be achieved"


print ""

print "num t0 events: " + str(len(eventlist_t0)) + " (" + str(len(eventlist_t0)*3) + " bytes)"
print "num t1 events: " + str(len(eventlist_t1)) + " (" + str(len(eventlist_t1)*3) + " bytes)"
print "num t2 events: " + str(len(eventlist_t2)) + " (" + str(len(eventlist_t2)*3) + " bytes)"
print "num t3 events: " + str(len(eventlist_t3)) + " (" + str(len(eventlist_t3)*3) + " bytes)"
print "num v0 events: " + str(len(eventlist_v0)) + " (" + str(len(eventlist_v0)*3) + " bytes)"
print "num v1 events: " + str(len(eventlist_v1)) + " (" + str(len(eventlist_v1)*3) + " bytes)"
print "num v2 events: " + str(len(eventlist_v2)) + " (" + str(len(eventlist_v2)*3) + " bytes)"
print "num v3 events: " + str(len(eventlist_v3)) + " (" + str(len(eventlist_v3)*3) + " bytes)"

total_volume_events = len(eventlist_v0) + len(eventlist_v1) + len(eventlist_v2) + len(eventlist_v3)
total_tone_events = len(eventlist_t0) + len(eventlist_t1) + len(eventlist_t2) + len(eventlist_t3)
size_volume_events = (total_volume_events * 4 / 8) + total_volume_events*2 / 4
size_tone_events = (total_tone_events * 10 / 8) + total_tone_events*2

print "total_volume_events = " + str(total_volume_events) + " (" + str(size_volume_events) + " bytes)"
print "total_tone_events = " + str(total_tone_events) + " (" + str(size_tone_events) + " bytes)"


# seems you can playback at any frequency, by simply processing the VGM data stream to catchup with the simulated/real time
# this implies a bunch of registers will be written in one go. So for any tones or volumes that duplicate within the time slot, we can eliminate those
# therefore, you could in principle 'resample' a VGM at a given update frequency (eg. 50Hz) which would eliminate any redundant data sampled at 44100 hz

# basically, we'd play the song at a given playback rate, capture the output, and rewrite the VGM with these new values.
# we can test the process in the web player to see if any fidelity would be lost.
# at the very least, the wait time numbers would be smaller and therefore easier to pack
#
# another solution is to splice a tune into repeated patterns
#
# Alternatively, analyse the tune - assuming it was originally sequenced at some BPM, there would have to be a pattern
# Also, assume that instruments were used where tone/volume envelopes were used
# Capture when tone changes happen, then look for the volume patterns to create instruments
# then re-sequence as an instrument/pattern based format



vgm_data.write_vgm(output_filename)



