import nntplib
from tkinter import E, N
from memory import Memory
from typing import List

def i8(v: int) -> int:
	return ((v & 0xFF) ^ 0x80) - 0x80

def u8(v: int) -> int:
	return v & 0xFF

def u16(v):
	return v & 0xFFFF

class opCodeTable:
	def __init__(self, mem: Memory):
		# 16-bit registers that are made up of two smaller 8-bit registers
		# ex. AF = A(upper 8 bit register) + F(lower 8 bit register) = 16-bit register
		self.AF = 0x0100
		self.BC = 0x0013
		self.DE = 0x00D8
		self.HL = 0x014D
		
		# strictly 16-bit only
		self.SP = 0xFFFE # stack pointer
		self.PC = 0x0100 # program counter

		# CPU Flags (used to perform conditional branching AKA if statements)
		# NOTE: each represent 1 bit and together are the upper 4 bits of the F register
		self.Z = 1 # zero flag
		self.N = 0 # negative (AKA substract) flag
		self.H = 1 # half-carry flag
		self.C = 1 # carry flag

		self.mem = mem

		# interrupt master enable: if unset, interrupts absolutely cannot happen
		self.ime = 0

		# if set, delays setting ime by 1 M-Cycle
		self.delayed_ime_enable = False

	def flag_bits(self) -> int:
		return (self.Z << 7) | (self.N << 6) | (self.H << 5) | (self.C << 4)

	def read_imm_u16(self):
		lsb = self.mem.read(self.PC)
		self.PC = u16(self.PC + 1)
		msb = self.mem.read(self.PC)
		self.PC = u16(self.PC + 1)
		return (msb << 8) | lsb

	def read_imm_u8(self):
		byte = self.mem.read(self.PC)
		self.PC = u16(self.PC + 1)
		return byte

	def execute_prefixed(self):
		#prefixed table: 00-FF, no blanks
		lst = self.mem.read(self.PC)
		print(hex(lst))
		self.PC = (self.PC + 1) & 0xFFFF
		match lst:
			case 0x00: #RLC B
				self.BC = (u8((self.BC >> 8) << 1) << 8) | ((self.BC >> 15) << 8) | (self.BC & 0x00FF)
				self.Z = (self.BC >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.BC >> 8) & 1
			case 0x01: #RLC C
				self.BC = (self.BC & 0xFF00) | ((self.BC << 1) & 0xFE) | (((self.BC << 1) >> 8) & 1)
				self.Z = (self.BC & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = self.BC & 1
			case 0x02: #RLC D
				self.DE = (u8((self.DE >> 8) << 1) << 8) | ((self.DE >> 15) << 8) | (self.DE & 0x00FF)
				self.Z = (self.DE >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.DE >> 8) & 1
			case 0x03: #RLC E
				self.DE = (self.DE & 0xFF00) | ((self.DE << 1) & 0xFE) | (((self.DE << 1) >> 8) & 1)
				self.Z = (self.DE & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = self.DE & 1
			case 0x04: #RLC H
				self.HL = (u8((self.HL >> 8) << 1) << 8) | ((self.HL >> 15) << 8) | (self.HL & 0x00FF)
				self.Z = (self.HL >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.HL >> 8) & 1
			case 0x05: #RLC L
				self.HL = (self.HL & 0xFF00) | ((self.HL << 1) & 0xFE) | (((self.HL << 1) >> 8) & 1)
				self.Z = (self.HL & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = self.HL & 1
			case 0x06: #RLC (HL) rotate memory contents
				v = self.mem.read(self.HL)
				v = u8(v << 1) | (v >> 7)
				self.mem.write(self.HL, v)
				self.Z = v == 0
				self.N = 0
				self.H = 0
				self.C = v & 1
			case 0x07: #RLC A
				self.AF = (u8((self.AF >> 8) << 1) << 8) | ((self.AF >> 15) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.AF >> 8) & 1
			case 0x08: #RRC B
				self.BC = (u8((self.BC >> 8) >> 1) << 8) | (u8((self.BC >> 8) << 7) << 8) | (self.BC & 0x00FF)
				self.Z = (self.BC >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.BC >> 15) & 1
			case 0x09: #RRC C
				self.BC = (self.BC & 0xFF00) | ((self.BC >> 1) & 0x7F) | u8((self.BC & 0xFF) << 7)
				self.Z = (self.BC & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = (self.BC >> 7) & 1
			case 0x0A: #RRC D
				self.DE = (u8((self.DE >> 8) >> 1) << 8) | (u8((self.DE >> 8) << 7) << 8) | (self.DE & 0x00FF)
				self.Z = (self.DE >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.DE >> 15) & 1
			case 0x0B: #RRC E
				self.DE = (self.DE & 0xFF00) | ((self.DE >> 1) & 0x7F) | u8((self.DE & 0xFF) << 7)
				self.Z = (self.DE & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = (self.DE >> 7) & 1
			case 0x0C: #RRC H
				self.HL = (u8((self.HL >> 8) >> 1) << 8) | (u8((self.HL >> 8) << 7) << 8) | (self.HL & 0x00FF)
				self.Z = (self.HL >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.HL >> 15) & 1
			case 0x0D: #RRC L
				self.HL = (self.HL & 0xFF00) | ((self.HL >> 1) & 0x7F) | u8((self.HL & 0xFF) << 7)
				self.Z = (self.HL & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = (self.HL >> 7) & 1
			case 0x0E: #RRC (HL)
				v = self.mem.read(self.HL)
				v = u8(v >> 1) | u8(v << 7)
				self.mem.write(self.HL, v)
				self.Z = v == 0
				self.N = 0
				self.H = 0
				self.C = (v >> 7) & 1
			case 0x0F: #RRC A
				self.AF = (u8((self.AF >> 8) >> 1) << 8) | (u8((self.AF >> 8) << 7) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.AF >> 15) & 1

			case 0x10: #RL B
				temp = self.C
				self.C = (self.BC >> 15) & 1
				self.BC = (((((self.BC >> 8) << 1) & 0xFF) | temp) << 8)  | (self.BC & 0x00FF)
				self.Z = (self.BC >> 8) == 0
				self.N = 0
				self.H = 0
			case 0x11: #RL C
				temp = self.C
				self.C = (self.BC >> 7) & 1
				self.BC = (self.BC & 0xFF00) | ((self.BC << 1) & 0xFF)  | (((self.BC << 1) >> 8) & 1)
				self.BC = ((self.BC >> 1) << 1) | temp
				self.Z = (self.BC & 0xFF) == 0
				self.N = 0
				self.H = 0
			case 0x12: #RL D
				temp = self.C
				self.C = (self.DE >> 15) & 1
				self.DE = (((((self.DE >> 8) << 1) & 0xFF) | temp) << 8)  | (self.DE & 0x00FF)
				self.Z = (self.DE >> 8) == 0
				self.N = 0
				self.H = 0
			case 0x13: #RL E
				temp = self.C
				self.C = (self.DE >> 7) & 1
				self.DE = (self.DE & 0xFF00) | ((self.DE << 1) & 0xFF)  | (((self.DE << 1) >> 8) & 1)
				self.DE = ((self.DE >> 1) << 1) | temp
				self.Z = (self.DE & 0xFF) == 0
				self.N = 0
				self.H = 0
			case 0x14: #RL H
				temp = self.C
				self.C = (self.HL >> 15) & 1
				self.HL = (((((self.HL >> 8) << 1) & 0xFF) | temp) << 8)  | (self.HL & 0x00FF)
				self.Z = (self.HL >> 8) == 0
				self.N = 0
				self.H = 0
			case 0x15: #RL L
				temp = self.C
				self.C = (self.HL >> 7) & 1
				self.HL = (self.HL & 0xFF00) | ((self.HL << 1) & 0xFF)  | (((self.HL << 1) >> 8) & 1)
				self.HL = ((self.HL >> 1) << 1) | temp
				self.Z = (self.HL & 0xFF) == 0
				self.N = 0
				self.H = 0
			case 0x16: #RL (HL) rotate memory contents
				v = self.mem.read(self.HL)
				temp = self.C
				self.C = (v >> 15) & 1
				v = u8(v << 1) | (v >> 7)
				v = ((v >> 1) << 1) | temp
				self.mem.write(self.HL, v)
				self.Z = v == 0
				self.N = 0
				self.H = 0
			case 0x17: #RL A
				temp = self.C
				self.C = (self.AF >> 15) & 1
				self.AF = (((((self.AF >> 8) << 1) & 0xFF) | temp) << 8)  | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
			case 0x18: #RR B
				temp = self.C
				self.C = (self.BC >> 8) & 1
				self.BC = (u8((self.BC >> 8) >> 1) << 8) | (u8((self.BC >> 8) << 7) << 8) | (self.BC & 0x00FF)
				self.BC = (((u8((self.BC >> 8) << 1) >> 1) | (temp << 7)) << 8) | (self.BC & 0x00FF)
				self.Z = (self.BC >> 8) == 0
				self.N = 0
				self.H = 0
			case 0x19: #RR C
				temp = self.C
				self.C = self.BC & 1
				self.BC = (self.BC & 0xFF00) | ((self.BC >> 1) & 0x7F) | (temp << 7)
				self.Z = (self.BC & 0xFF) == 0
				self.N = 0
				self.H = 0
			case 0x1A: #RR D
				temp = self.C
				self.C = (self.DE >> 8) & 1
				self.DE = (u8((self.DE >> 8) >> 1) << 8) | (u8((self.DE >> 8) << 7) << 8) | (self.DE & 0x00FF)
				self.DE = (((u8((self.DE >> 8) << 1) >> 1) | (temp << 7)) << 8) | (self.DE & 0x00FF)
				self.Z = (self.DE >> 8) == 0
				self.N = 0
				self.H = 0
			case 0x1B: #RR E
				temp = self.C
				self.C = self.DE & 1
				self.DE = (self.DE & 0xFF00) | ((self.DE >> 1) & 0x7F) | (temp << 7)
				self.Z = (self.DE & 0xFF) == 0
				self.N = 0
				self.H = 0
			case 0x1C: #RR H
				temp = self.C
				self.C = (self.HL >> 8) & 1
				self.HL = (u8((self.HL >> 8) >> 1) << 8) | (u8((self.HL >> 8) << 7) << 8) | (self.HL & 0x00FF)
				self.HL = (((u8((self.HL >> 8) << 1) >> 1) | (temp << 7)) << 8) | (self.HL & 0x00FF)
				self.Z = (self.HL >> 8) == 0
				self.N = 0
				self.H = 0
			case 0x1D: #RR L
				temp = self.C
				self.C = self.HL & 1
				self.HL = (self.HL & 0xFF00) | ((self.HL >> 1) & 0x7F) | (temp << 7)
				self.Z = (self.HL & 0xFF) == 0
				self.N = 0
				self.H = 0
			case 0x1E: #RR (HL)
				v = self.mem.read(self.HL)
				temp = self.C
				self.C = v & 1
				v = u8(v >> 1) | temp << 7
				self.mem.write(self.HL, v)
				self.Z = v == 0
				self.N = 0
				self.H = 0
				self.C = (v >> 7) & 1
			case 0x1F: #RR A
				temp = self.C
				self.C = (self.AF >> 8) & 1
				self.AF = (u8((self.AF >> 8) >> 1) << 8) | (u8((self.AF >> 8) << 7) << 8) | (self.AF & 0x00FF)
				self.AF = (((u8((self.AF >> 8) << 1) >> 1) | (temp << 7)) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0

			case 0x20: #SLA B
				self.BC = (u8((self.BC >> 8) << 1) << 8) |  (self.BC & 0x00FF)
				self.Z = (self.BC >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.BC >> 8) & 1
			case 0x21: #SLA C
				self.BC = (self.BC & 0xFF00) | ((self.BC << 1) & 0xFE)
				self.Z = (self.BC & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = self.BC & 1
			case 0x22: #SLA D
				self.DE = (u8((self.DE >> 8) << 1) << 8) | (self.DE & 0x00FF)
				self.Z = (self.DE >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.DE >> 8) & 1
			case 0x23: #SLA E
				self.DE = (self.DE & 0xFF00) | ((self.DE << 1) & 0xFE)
				self.Z = (self.DE & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = self.DE & 1
			case 0x24: #SLA H
				self.HL = (u8((self.HL >> 8) << 1) << 8) | (self.HL & 0x00FF)
				self.Z = (self.HL >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.HL >> 8) & 1
			case 0x25: #SLA L
				self.HL = (self.HL & 0xFF00) | ((self.HL << 1) & 0xFE)
				#| (((self.HL << 1) >> 8) & 1)
				self.Z = (self.HL & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = self.HL & 1
			case 0x26: #SLA (HL) rotate memory contents
				v = self.mem.read(self.HL)
				v = u8(v << 1) 
				#| (v >> 7)
				self.mem.write(self.HL, v)
				self.Z = v == 0
				self.N = 0
				self.H = 0
				self.C = v & 1
			case 0x27: #SLA A
				self.AF = (u8((self.AF >> 8) << 1) << 8) | (self.AF & 0x00FF)
				#((self.AF >> 15) << 8) |
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.AF >> 8) & 1
			case 0x28: #SLA B
				#self.BC = (u8((self.BC >> 8) >> 1) << 8) | (u8((self.BC >> 8) << 7) << 8) | (self.BC & 0x00FF)
				self.BC = (u8((self.BC >> 8) >> 1) << 8) | ((self.BC >> 15) << 15) | (self.BC & 0x00FF)
				self.Z = (self.BC >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.BC >> 15) & 1
			case 0x29: #SLA C
				#self.BC = (self.BC & 0xFF00) | ((self.BC >> 1) & 0x7F) | u8((self.BC & 0xFF) << 7)
				self.BC = (self.BC & 0xFF00) | ((self.BC >> 1) & 0x7F) | ((u8(self.BC & 0xFF) >> 7) << 7)
				self.Z = (self.BC & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = (self.BC >> 7) & 1
			case 0x2A: #SLA D
				self.DE = (u8((self.DE >> 8) >> 1) << 8) | ((self.DE >> 15) << 15) | (self.DE & 0x00FF)
				self.Z = (self.DE >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.DE >> 15) & 1
			case 0x2B: #SLA E
				self.DE = (self.DE & 0xFF00) | ((self.DE >> 1) & 0x7F) | ((u8(self.DE & 0xFF) >> 7) << 7)
				self.Z = (self.DE & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = (self.DE >> 7) & 1
			case 0x2C: #SLA H
				self.HL = (u8((self.HL >> 8) >> 1) << 8) | ((self.HL >> 15) << 15) | (self.HL & 0x00FF)
				self.Z = (self.HL >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.HL >> 15) & 1
			case 0x2D: #SLA L
				self.HL = (self.HL & 0xFF00) | ((self.HL >> 1) & 0x7F) | ((u8(self.HL & 0xFF) >> 7) << 7)
				self.Z = (self.HL & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = (self.HL >> 7) & 1
			case 0x2E: #SLA (HL)
				v = self.mem.read(self.HL)
				#v = u8(v >> 1) | u8(v << 7)
				v = u8(v >> 1) | u8((v >> 7) << 7)
				self.mem.write(self.HL, v)
				self.Z = v == 0
				self.N = 0
				self.H = 0
				self.C = (v >> 7) & 1
			case 0x2F: #SLA A
				self.AF = (u8((self.AF >> 8) >> 1) << 8) | ((self.AF >> 15) << 15) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.AF >> 15) & 1

			case 0x30: #SWAP B first half of B is switched with last half and vice versa
				#print("{:b}".format(self.BC >> 8))
				#print("{:b}".format(u8((self.BC >> 8) << 4))) #rhalf
				#print("{:b}".format(u8((self.BC >> 8) >> 4))) #lhalf
				#print("{:b}".format((u8((self.BC >> 8) << 4) | u8((self.BC >> 8) >> 4)) << 8))
				self.BC = ((u8((self.BC >> 8) << 4) | u8((self.BC >> 8) >> 4)) << 8) | (self.BC & 0x00FF)
				self.Z = (self.BC >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0#(self.BC >> 8) & 1
			case 0x31: #SWAP C
				self.BC = (self.BC & 0xFF00) | ((u8((self.BC & 0xFF) << 4) | u8((self.BC & 0xFF) >> 4)))
				self.Z = (self.BC & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = 0#self.BC & 1
			case 0x32: #SWAP D
				self.DE = ((u8((self.DE >> 8) << 4) | u8((self.DE >> 8) >> 4)) << 8) | (self.DE & 0x00FF)
				self.Z = (self.DE >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0#(self.BC >> 8) & 1
			case 0x33: #SWAP E
				self.DE = (self.DE & 0xFF00) | ((u8((self.DE & 0xFF) << 4) | u8((self.DE & 0xFF) >> 4)))
				self.Z = (self.DE & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = 0#self.BC & 1
			case 0x34: #SWAP H
				self.HL = ((u8((self.HL >> 8) << 4) | u8((self.HL >> 8) >> 4)) << 8) | (self.HL & 0x00FF)
				self.Z = (self.HL >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0#(self.BC >> 8) & 1
			case 0x35: #SWAP L
				self.HL = (self.HL & 0xFF00) | ((u8((self.HL & 0xFF) << 4) | u8((self.HL & 0xFF) >> 4)))
				self.Z = (self.HL & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = 0#self.BC & 1
			case 0x36: #SWAP (HL)
				v = self.mem.read(self.HL)
				v = u8(v << 4) | (v >> 4)
				self.mem.write(self.HL, v)
				self.Z = v == 0
				self.N = 0
				self.H = 0
				self.C = 0#v & 1
			case 0x37: #SWAP A
				self.AF = ((u8((self.AF >> 8) << 4) | u8((self.AF >> 8) >> 4)) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0#(self.BC >> 8) & 1
			case 0x38: #SRL B
				self.BC = (u8((self.BC >> 8) >> 1) << 8) | (self.BC & 0x00FF)
				#| (u8((self.BC >> 8) << 7) << 8)
				self.Z = (self.BC >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.BC >> 15) & 1
			case 0x39: #SRL C
				self.BC = (self.BC & 0xFF00) | ((self.BC >> 1) & 0x7F)# | u8((self.BC & 0xFF) << 7)
				self.Z = (self.BC & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = (self.BC >> 7) & 1
			case 0x3A: #SRL D
				self.DE = (u8((self.DE >> 8) >> 1) << 8) | (self.DE & 0x00FF)
				self.Z = (self.DE >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.DE >> 15) & 1
			case 0x3B: #SRL E
				self.DE = (self.DE & 0xFF00) | ((self.DE >> 1) & 0x7F)
				self.Z = (self.DE & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = (self.DE >> 7) & 1
			case 0x3C: #SRL H
				self.HL = (u8((self.HL >> 8) >> 1) << 8) | (self.HL & 0x00FF)
				self.Z = (self.HL >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.HL >> 15) & 1
			case 0x3D: #SRL L
				self.HL = (self.HL & 0xFF00) | ((self.HL >> 1) & 0x7F)
				self.Z = (self.HL & 0xFF) == 0
				self.N = 0
				self.H = 0
				self.C = (self.HL >> 7) & 1
			case 0x3E: #SRL (HL)
				v = self.mem.read(self.HL)
				v = u8(v >> 1)# | u8(v << 7)
				self.mem.write(self.HL, v)
				self.Z = v == 0
				self.N = 0
				self.H = 0
				self.C = (v >> 7) & 1
			case 0x3F: #SRL A
				self.AF = (u8((self.AF >> 8) >> 1) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = (self.AF >> 15) & 1

			case 0x40:# 40-7f: Bit 0-7, all registers
				self.Z = (self.BC >> 8) & 1
				self.N = 0
				self.H = 0
			case 0x41:
				self.Z = (self.BC & 0xFF) & 1
				self.N = 0
				self.H = 0
			case 0x42:
				self.Z = (self.DE >> 8) & 1
				self.N = 0
				self.H = 0
			case 0x43:
				self.Z = (self.DE & 0xFF) & 1
				self.N = 0
				self.H = 0
			case 0x44:
				self.Z = (self.HL >> 8) & 1
				self.N = 0
				self.H = 0
			case 0x45:
				self.Z = (self.HL & 0xFF) & 1
				self.N = 0
				self.H = 0
			case 0x46:
				v = self.mem.read(self.HL)
				self.Z = v & 1
				self.N = 0
				self.H = 0
			case 0x47:
				self.Z = (self.AF >> 8) & 1
				self.N = 0
				self.H = 0
			case 0x48:
				self.Z = (self.BC >> 8 >> 1) & 1
				self.N = 0
				self.H = 0
			case 0x49:
				self.Z = (self.BC & 0xFF >> 1) & 1
				self.N = 0
				self.H = 0
			case 0x4a:
				self.Z = (self.DE >> 8 >> 1) & 1
				self.N = 0
				self.H = 0
			case 0x4b:
				self.Z = (self.DE & 0xFF >> 1) & 1
				self.N = 0
				self.H = 0
			case 0x4c:
				self.Z = (self.HL >> 8 >> 1) & 1
				self.N = 0
				self.H = 0
			case 0x4d:
				self.Z = (self.HL & 0xFF >> 1) & 1
				self.N = 0
				self.H = 0
			case 0x4e:
				v = self.mem.read(self.HL)
				self.Z = (v >> 1) & 1
				self.N = 0
				self.H = 0
			case 0x4f:
				self.Z = (self.AF >> 8 >> 1) & 1
				self.N = 0
				self.H = 0
			
			case 0x50:
				self.Z = (self.BC >> 8 >> 2) & 1
				self.N = 0
				self.H = 0
			case 0x51:
				self.Z = (self.BC & 0xFF >> 2) & 1
				self.N = 0
				self.H = 0
			case 0x52:
				self.Z = (self.DE >> 8 >> 2) & 1
				self.N = 0
				self.H = 0
			case 0x53:
				self.Z = (self.DE & 0xFF >> 2) & 1
				self.N = 0
				self.H = 0
			case 0x54:
				self.Z = (self.HL >> 8 >> 2) & 1
				self.N = 0
				self.H = 0
			case 0x55:
				self.Z = (self.HL & 0xFF >> 2) & 1
				self.N = 0
				self.H = 0
			case 0x56:
				v = self.mem.read(self.HL)
				self.Z = (v >> 2) & 1
				self.N = 0
				self.H = 0
			case 0x57:
				self.Z = (self.AF >> 8 >> 2) & 1
				self.N = 0
				self.H = 0
			case 0x58:
				self.Z = (self.BC >> 8 >> 3) & 1
				self.N = 0
				self.H = 0
			case 0x59:
				self.Z = (self.BC & 0xFF >> 3) & 1
				self.N = 0
				self.H = 0
			case 0x5a:
				self.Z = (self.DE >> 8 >> 3) & 1
				self.N = 0
				self.H = 0
			case 0x5b:
				self.Z = (self.DE & 0xFF >> 3) & 1
				self.N = 0
				self.H = 0
			case 0x5c:
				self.Z = (self.HL >> 8 >> 3) & 1
				self.N = 0
				self.H = 0
			case 0x5d:
				self.Z = (self.HL & 0xFF >> 3) & 1
				self.N = 0
				self.H = 0
			case 0x5e:
				v = self.mem.read(self.HL)
				self.Z = (v >> 3) & 1
				self.N = 0
				self.H = 0
			case 0x5f:
				self.Z = (self.AF >> 8 >> 3) & 1
				self.N = 0
				self.H = 0
			
			case 0x60:
				self.Z = (self.BC >> 8 >> 4) & 1
				self.N = 0
				self.H = 0
			case 0x61:
				self.Z = (self.BC & 0xFF >> 4) & 1
				self.N = 0
				self.H = 0
			case 0x62:
				self.Z = (self.DE >> 8 >> 4) & 1
				self.N = 0
				self.H = 0
			case 0x63:
				self.Z = (self.DE & 0xFF >> 4) & 1
				self.N = 0
				self.H = 0
			case 0x64:
				self.Z = (self.HL >> 8 >> 4) & 1
				self.N = 0
				self.H = 0
			case 0x65:
				self.Z = (self.HL & 0xFF >> 4) & 1
				self.N = 0
				self.H = 0
			case 0x66:
				v = self.mem.read(self.HL)
				self.Z = (v >> 4) & 1
				self.N = 0
				self.H = 0
			case 0x67:
				self.Z = (self.AF >> 8 >> 4) & 1
				self.N = 0
				self.H = 0
			case 0x68:
				self.Z = (self.BC >> 8 >> 5) & 1
				self.N = 0
				self.H = 0
			case 0x69:
				self.Z = (self.BC & 0xFF >> 5) & 1
				self.N = 0
				self.H = 0
			case 0x6a:
				self.Z = (self.DE >> 8 >> 5) & 1
				self.N = 0
				self.H = 0
			case 0x6b:
				self.Z = (self.DE & 0xFF >> 5) & 1
				self.N = 0
				self.H = 0
			case 0x6c:
				self.Z = (self.HL >> 8 >> 5) & 1
				self.N = 0
				self.H = 0
			case 0x6d:
				self.Z = (self.HL & 0xFF >> 5) & 1
				self.N = 0
				self.H = 0
			case 0x6e:
				v = self.mem.read(self.HL)
				self.Z = (v >> 5) & 1
				self.N = 0
				self.H = 0
			case 0x6f:
				self.Z = (self.AF >> 8 >> 5) & 1
				self.N = 0
				self.H = 0
			
			case 0x70:
				self.Z = (self.BC >> 8 >> 6) & 1
				self.N = 0
				self.H = 0
			case 0x71:
				self.Z = (self.BC & 0xFF >> 6) & 1
				self.N = 0
				self.H = 0
			case 0x72:
				self.Z = (self.DE >> 8 >> 6) & 1
				self.N = 0
				self.H = 0
			case 0x73:
				self.Z = (self.DE & 0xFF >> 6) & 1
				self.N = 0
				self.H = 0
			case 0x74:
				self.Z = (self.HL >> 8 >> 6) & 1
				self.N = 0
				self.H = 0
			case 0x75:
				self.Z = (self.HL & 0xFF >> 6) & 1
				self.N = 0
				self.H = 0
			case 0x76:
				v = self.mem.read(self.HL)
				self.Z = (v >> 6) & 1
				self.N = 0
				self.H = 0
			case 0x77:
				self.Z = (self.AF >> 8 >> 6) & 1
				self.N = 0
				self.H = 0
			case 0x78:
				self.Z = (self.BC >> 8 >> 7) & 1
				self.N = 0
				self.H = 0
			case 0x79:
				self.Z = (self.BC & 0xFF >> 7) & 1
				self.N = 0
				self.H = 0
			case 0x7a:
				self.Z = (self.DE >> 8 >> 7) & 1
				self.N = 0
				self.H = 0
			case 0x7b:
				self.Z = (self.DE & 0xFF >> 7) & 1
				self.N = 0
				self.H = 0
			case 0x7c:
				self.Z = (self.HL >> 8 >> 7) & 1
				self.N = 0
				self.H = 0
			case 0x7d:
				self.Z = (self.HL & 0xFF >> 7) & 1
				self.N = 0
				self.H = 0
			case 0x7e:
				v = self.mem.read(self.HL)
				self.Z = (v >> 7) & 1
				self.N = 0
				self.H = 0
			case 0x7f:
				self.Z = (self.AF >> 8 >> 7) & 1
				self.N = 0
				self.H = 0

			case 0x80: #80-BF RES bit 0-7, all registers
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) & ~(1 << 0)) << 8)
			case 0x81:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) & ~(1 << 0))
			case 0x82:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) & ~(1 << 0)) << 8)
			case 0x83:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) & ~(1 << 0))  
			case 0x84:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) & ~(1 << 0)) << 8)   
			case 0x85:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) & ~(1 << 0))    
			case 0x86:
				v = self.mem.read(self.HL)
				v &= ~(1 << 0)
				self.mem.write(self.HL, v)
			case 0x87:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) & ~(1 << 0)) << 8)
			case 0x88:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) & ~(1 << 1)) << 8)
			case 0x89:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) & ~(1 << 1))
			case 0x8a:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) & ~(1 << 1)) << 8)
			case 0x8b:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) & ~(1 << 1)) 
			case 0x8c:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) & ~(1 << 1)) << 8)
			case 0x8d:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) & ~(1 << 1)) 
			case 0x8e:
				v = self.mem.read(self.HL)
				v &= ~(1 << 1)
				self.mem.write(self.HL, v)
			case 0x8f:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) & ~(1 << 1)) << 8)
			
			case 0x90:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) & ~(1 << 2)) << 8)
			case 0x91:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) & ~(1 << 2))
			case 0x92:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) & ~(1 << 2)) << 8)
			case 0x93:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) & ~(1 << 2))  
			case 0x94:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) & ~(1 << 2)) << 8)   
			case 0x95:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) & ~(1 << 2))    
			case 0x96:
				v = self.mem.read(self.HL)
				v &= ~(1 << 2)
				self.mem.write(self.HL, v)
			case 0x97:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) & ~(1 << 2)) << 8)
			case 0x98:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) & ~(1 << 3)) << 8)
			case 0x99:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) & ~(1 << 3))
			case 0x9a:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) & ~(1 << 3)) << 8)
			case 0x9b:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) & ~(1 << 3)) 
			case 0x9c:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) & ~(1 << 3)) << 8)
			case 0x9d:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) & ~(1 << 3)) 
			case 0x9e:
				v = self.mem.read(self.HL)
				v &= ~(1 << 3)
				self.mem.write(self.HL, v)
			case 0x9f:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) & ~(1 << 3)) << 8)
			
			case 0xa0:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) & ~(1 << 4)) << 8)
			case 0xa1:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) & ~(1 << 4))
			case 0xa2:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) & ~(1 << 4)) << 8)
			case 0xa3:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) & ~(1 << 4))  
			case 0xa4:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) & ~(1 << 4)) << 8)   
			case 0xa5:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) & ~(1 << 4))    
			case 0xa6:
				v = self.mem.read(self.HL)
				v &= ~(1 << 4)
				self.mem.write(self.HL, v)
			case 0xa7:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) & ~(1 << 4)) << 8)
			case 0xa8:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) & ~(1 << 5)) << 8)
			case 0xa9:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) & ~(1 << 5))
			case 0xaa:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) & ~(1 << 5)) << 8)
			case 0xab:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) & ~(1 << 5)) 
			case 0xac:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) & ~(1 << 5)) << 8)
			case 0xad:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) & ~(1 << 5)) 
			case 0xae:
				v = self.mem.read(self.HL)
				v &= ~(1 << 5)
				self.mem.write(self.HL, v)
			case 0xaf:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) & ~(1 << 5)) << 8)
				
			case 0xb0:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) & ~(1 << 6)) << 8)
			case 0xb1:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) & ~(1 << 6))
			case 0xb2:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) & ~(1 << 6)) << 8)
			case 0xb3:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) & ~(1 << 6))  
			case 0xb4:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) & ~(1 << 6)) << 8)   
			case 0xb5:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) & ~(1 << 6))    
			case 0xb6:
				v = self.mem.read(self.HL)
				v &= ~(1 << 6)
				self.mem.write(self.HL, v)
			case 0xb7:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) & ~(1 << 6)) << 8)
			case 0xb8:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) & ~(1 << 7)) << 8)
			case 0xb9:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) & ~(1 << 7))
			case 0xba:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) & ~(1 << 7)) << 8)
			case 0xbb:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) & ~(1 << 7)) 
			case 0xbc:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) & ~(1 << 7)) << 8)
			case 0xbd:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) & ~(1 << 7)) 
			case 0xbe:
				v = self.mem.read(self.HL)
				v &= ~(1 << 7)
				self.mem.write(self.HL, v)
			case 0xbf:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) & ~(1 << 7)) << 8)

			case 0xc0:#C0-FF SET bit 0-7, all registers
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) | (1 << 0)) << 8)
			case 0xc1:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) | (1 << 0))
			case 0xc2:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) | (1 << 0)) << 8)
			case 0xc3:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) | (1 << 0))  
			case 0xc4:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) | (1 << 0)) << 8)   
			case 0xc5:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) | (1 << 0))    
			case 0xc6:
				v = self.mem.read(self.HL)
				v |= (1 << 0)
				self.mem.write(self.HL, v)
			case 0xc7:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) | (1 << 0)) << 8)
			case 0xc8:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) | (1 << 1)) << 8)
			case 0xc9:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) | (1 << 1))
			case 0xca:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) | (1 << 1)) << 8)
			case 0xcb:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) | (1 << 1)) 
			case 0xcc:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) | (1 << 1)) << 8)
			case 0xcd:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) | (1 << 1)) 
			case 0xce:
				v = self.mem.read(self.HL)
				v |= (1 << 1)
				self.mem.write(self.HL, v)
			case 0xcf:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) | (1 << 1)) << 8)
			
			case 0xd0:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) | (1 << 2)) << 8)
			case 0xd1:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) | (1 << 2))
			case 0xd2:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) | (1 << 2)) << 8)
			case 0xd3:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) | (1 << 2))  
			case 0xd4:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) | (1 << 2)) << 8)   
			case 0xd5:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) | (1 << 2))    
			case 0xd6:
				v = self.mem.read(self.HL)
				v |= (1 << 2)
				self.mem.write(self.HL, v)
			case 0xd7:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) | (1 << 2)) << 8)
			case 0xd8:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) | (1 << 3)) << 8)
			case 0xd9:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) | (1 << 3))
			case 0xda:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) | (1 << 3)) << 8)
			case 0xdb:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) | (1 << 3)) 
			case 0xdc:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) | (1 << 3)) << 8)
			case 0xdd:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) | (1 << 3)) 
			case 0xde:
				v = self.mem.read(self.HL)
				v |= (1 << 3)
				self.mem.write(self.HL, v)
			case 0xdf:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) | (1 << 3)) << 8)
			
			case 0xe0:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) | (1 << 4)) << 8)
			case 0xe1:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) | (1 << 4))
			case 0xe2:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) | (1 << 4)) << 8)
			case 0xe3:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) | (1 << 4))  
			case 0xe4:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) | (1 << 4)) << 8)   
			case 0xe5:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) | (1 << 4))    
			case 0xe6:
				v = self.mem.read(self.HL)
				v |= (1 << 4)
				self.mem.write(self.HL, v)
			case 0xe7:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) | (1 << 4)) << 8)
			case 0xe8:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) | (1 << 5)) << 8)
			case 0xe9:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) | (1 << 5))
			case 0xea:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) | (1 << 5)) << 8)
			case 0xeb:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) | (1 << 5)) 
			case 0xec:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) | (1 << 5)) << 8)
			case 0xed:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) | (1 << 5)) 
			case 0xee:
				v = self.mem.read(self.HL)
				v |= (1 << 5)
				self.mem.write(self.HL, v)
			case 0xef:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) | (1 << 5)) << 8)
				
			case 0xf0:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) | (1 << 6)) << 8)
			case 0xf1:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) | (1 << 6))
			case 0xf2:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) | (1 << 6)) << 8)
			case 0xf3:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) | (1 << 6))  
			case 0xf4:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) | (1 << 6)) << 8)   
			case 0xf5:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) | (1 << 6))    
			case 0xf6:
				v = self.mem.read(self.HL)
				v |= (1 << 6)
				self.mem.write(self.HL, v)
			case 0xf7:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) | (1 << 6)) << 8)
			case 0xf8:
				self.BC = (self.BC & 0x00FF) | ((u8(self.BC >> 8) | (1 << 7)) << 8)
			case 0xf9:
				self.BC = (self.BC & 0xFF00) | ((self.BC & 0xFF) | (1 << 7))
			case 0xfa:
				self.DE = (self.DE & 0x00FF) | ((u8(self.DE >> 8) | (1 << 7)) << 8)
			case 0xfb:
				self.DE = (self.DE & 0xFF00) | ((self.DE & 0xFF) | (1 << 7)) 
			case 0xfc:
				self.HL = (self.HL & 0x00FF) | ((u8(self.HL >> 8) | (1 << 7)) << 8)
			case 0xfd:
				self.HL = (self.HL & 0xFF00) | ((self.HL & 0xFF) | (1 << 7)) 
			case 0xfe:
				v = self.mem.read(self.HL)
				v |= (1 << 7)
				self.mem.write(self.HL, v)
			case 0xff:
				self.AF = (self.AF & 0x00FF) | ((u8(self.AF >> 8) | (1 << 7)) << 8)

			case _:
				print("no code :(")
				exit(1)
		
	def tableLookup(self, code: int):
		match code:
			case 0xCB:
				self.execute_prefixed()

			case 0x00: #NOP
				pass
			case 0x01: #load immediate 2-bytes to BC
				nn = self.read_imm_u16()
				self.BC = nn
			case 0x02: #write BC to A
				self.mem.write(self.BC, self.AF >> 8)
			case 0x03: #increment BC
				self.BC = u16(self.BC + 1)
				self.mem.tick()
			case 0x04: #increment B
				v = u8((self.BC >> 8) + 1)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.BC >> 8) & 0xF) + 1) & 0x10) == 0x10
				self.BC = (v << 8) | (self.BC & 0x00FF)
			case 0x05: #decrement B
				v = u8((self.BC >> 8) - 1)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.BC >> 8) & 0xF) - (1 & 0xF)) & 0x10) == 0x10
				self.BC = (v << 8) | (self.BC & 0x00FF)
			case 0x06: #load immediate byte to B
				n = self.read_imm_u8()
				self.BC = (self.BC & 0x00FF) | (n << 8)
			case 0x07: #Rotate left circular (accumulator)
				self.AF = (u8((self.AF >> 8) << 1) << 8) | ((self.AF >> 15) << 8) | (self.AF & 0x00FF)
				self.Z = 0
				self.N = 0
				self.H = 0
				self.C = (self.AF >> 8) & 1
			case 0x08: #load the read 16-bits from the stack ptr
				nn = self.read_imm_u16()
				self.mem.write(nn, self.SP & 0xFF)
				self.mem.write(nn + 1, self.SP >> 8)
			case 0x09: #Add HL and BC together and store the result in HL
				self.N = 0
				self.H = (((self.HL & 0xFFF) + (self.BC & 0xFFF)) & 0x1000) == 0x1000
				self.C = ((self.HL + self.BC) & 0x10000) == 0x10000
				self.HL = u16(self.HL + self.BC)
				self.mem.tick()
			case 0x0A: #load contents of BC to A
				v = self.mem.read(self.BC)
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x0B: #BC--
				self.BC = u16(self.BC - 1)
				self.mem.tick()
			case 0x0C: #increment C
				v = u8((self.BC & 0xFF) + 1)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.BC & 0xFF) & 0xF) + 1) & 0x10) == 0x10
				self.BC = (self.BC & 0xFF00) | v
			case 0x0D: #decrement C
				v = u8((self.BC & 0xFF) - 1)
				self.Z = v == 0
				self.N = 1
				self.H = (((self.BC & 0xF) - 1) & 0x10) == 0x10
				self.BC = (self.BC & 0xFF00) | v
			case 0x0E: #Load the 8-bits to C
				n = self.read_imm_u8()
				self.BC = (self.BC & 0xFF00) | n
			case 0x0F: #Rotate right circular (accumulator)
				self.C = (self.AF >> 8) & 1
				self.AF = (u8(((self.AF >> 8) >> 1) | (self.C << 7)) << 8) | (self.AF & 0x00FF)
				self.Z = 0
				self.N = 0
				self.H = 0

			case 0x10: #STOP
				exit(1)
			case 0x11: #load immediate 2-bytes to DE
				nn = self.read_imm_u16()
				self.DE = nn
			case 0x12: #load A to DE
				self.mem.write(self.DE, (self.AF >> 8))
			case 0x13: #DE++
				self.DE = u16(self.DE + 1)
				self.mem.tick()
			case 0x14: #increment D
				v = u8((self.DE >> 8) + 1)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.DE >> 8) & 0xF) + 1) & 0x10) == 0x10
				self.DE = (v << 8) | (self.DE & 0x00FF)
			case 0x15: #decrement D
				v = u8((self.DE >> 8) - 1)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.DE >> 8) & 0xF) - (1 & 0xF)) & 0x10) == 0x10
				self.DE = (v << 8) | (self.DE & 0x00FF)
			case 0x16: #load immediate byte to D
				n = self.read_imm_u8()
				self.DE = (n << 8) | (self.DE & 0x00FF)
			case 0x17: #Rotate left (accumulator)
				v = (self.AF >> 8) << 1
				self.AF = (u8(v | self.C) << 8) | (self.AF & 0x00FF)
				self.Z = 0
				self.N = 0
				self.H = 0
				self.C = (v & 0x100) == 0x100
			case 0x18: #JR, e
				e = i8(self.read_imm_u8())
				self.PC = u16(self.PC + e)
				self.mem.tick()
			case 0x19: #Add HL and DE together and store the result in HL
				self.N = 0
				self.H = (((self.HL & 0xFFF) + (self.DE & 0xFFF)) & 0x1000) == 0x1000
				self.C = ((self.HL + self.DE) & 0x10000) == 0x10000
				self.HL = u16(self.HL + self.DE)
				self.mem.tick()
			case 0x1A: #load contents of DE to A
				v = self.mem.read(self.DE)
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x1B: #DE--
				self.DE = u16(self.DE - 1)
				self.mem.tick()
			case 0x1C: #increment E
				v = u8((self.DE & 0xFF) + 1)
				self.Z = v == 0
				self.N = 0
				self.H = (((self.DE & 0xF) + 1) & 0x10) == 0x10
				self.DE = (self.DE & 0xFF00) | v
			case 0x1D: #decrement E
				v = u8((self.DE & 0xFF) - 1)
				self.Z = v == 0
				self.N = 1
				self.H = (((self.DE & 0xF) - (1 & 0xF)) & 0x10) == 0x10
				self.DE = (self.DE & 0xFF00) | v
			case 0x1E: #Load the 8-bits to E
				n = self.read_imm_u8()
				self.DE = (self.DE & 0xFF00) | n
			case 0x1F: #Rotate Right (accumulator)
				prev_c = self.C
				self.C = (self.AF >> 8) & 1
				self.AF = (((self.AF >> 9) | (prev_c << 7)) << 8) | (self.AF & 0x00FF)
				self.Z = 0
				self.N = 0
				self.H = 0

			case 0x20: # JR NZ, e
				e = i8(self.mem.read(self.PC))
				self.PC = u16(self.PC + 1)
				if (not self.Z):
					self.PC = u16(self.PC + e)
					self.mem.tick()	
			case 0x21: #LD a16, HL
				nn = self.read_imm_u16()
				self.HL = nn
			case 0x22: #LD HL+
				self.mem.write(self.HL, self.AF >> 8)
				self.HL = u16(self.HL + 1)
			case 0x23: #inc HL
				self.HL = u16(self.HL + 1)
				self.mem.tick()
			case 0x24: #increment H
				v = u8((self.HL >> 8) + 1)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.HL >> 8) & 0xF) + 1) & 0x10) == 0x10
				self.HL = (v << 8) | (self.HL & 0x00FF)
			case 0x25: #decrement H
				v = u8((self.HL >> 8) - 1)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.HL >> 8) & 0xF) - (1 & 0xF)) & 0x10) == 0x10
				self.HL = (v << 8) | (self.HL & 0x00FF)
			case 0x26: #load immediate byte to H
				n = self.read_imm_u8()
				self.HL = (self.HL & 0x00FF) | (n << 8)
			# https://blog.ollien.com/posts/gb-daa/
			# https://github.com/Baekalfen/PyBoy/blob/934054c385d8027a98185fbb8f23f34f20903adb/pyboy/core/opcodes.py#L422 (thank you!)
			case 0x27: #Decimal adjust accumulator
				v = self.AF >> 8
				corr = 0
				corr |= 0x06 if (self.H != 0) else 0x00
				corr |= 0x60 if (self.C != 0) else 0x00

				if (self.N) != 0:
					v -= corr
				else:
					corr |= 0x06 if (v & 0x0F) > 0x09 else 0x00
					corr |= 0x60 if v > 0x99 else 0x00
					v += corr

				self.AF = (u8(v) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.H = 0
				self.C = (corr & 0x60) != 0
			case 0x28:
				e = i8(self.mem.read(self.PC))
				self.PC = u16(self.PC + 1)
				if (self.Z):
					self.PC = u16(self.PC + e)
					self.mem.tick()
			case 0x29:
				self.N = 0
				self.H = (((self.HL & 0xFFF) + (self.HL & 0xFFF)) & 0x1000) == 0x1000
				self.C = ((self.HL + self.HL) & 0x10000) == 0x10000
				self.HL = u16(self.HL + self.HL)
				self.mem.tick() # internal cycle
			case 0x2A:
				self.AF = (self.AF & 0x00FF) | (self.mem.read(self.HL) << 8)
				self.HL = u16(self.HL + 1)
			case 0x2B: #HL--
				self.HL = u16(self.HL - 1)
				self.mem.tick()
			case 0x2C: #increment L
				v = u8((self.HL & 0xFF) + 1)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.HL & 0xFF) & 0xF) + 1) & 0x10) == 0x10
				self.HL = (self.HL & 0xFF00) | v
			case 0x2D: #decrement L
				v = u8((self.HL & 0xFF) - 1)
				self.Z = v == 0
				self.N = 1
				self.H = (((self.HL & 0xF) - 1) & 0x10) == 0x10
				self.HL = (self.HL & 0xFF00) | v
			case 0x2E: #Load the 8-bits to L
				n = self.read_imm_u8()
				self.HL = (self.HL & 0xFF00) | n
			case 0x2F: #CPL, compliment of A
				self.AF = (((self.AF >> 8) ^ 0xFF) << 8) | (self.AF & 0x00FF)
				self.N = 1
				self.H = 1

			case 0x30: # JR NC, e
				e = i8(self.mem.read(self.PC))
				self.PC = u16(self.PC + 1)
				if (not self.C): # cc=true
					self.PC = u16(self.PC + e)
					self.mem.tick() # internal cycle
			case 0x31: # LD SP
				nn = self.read_imm_u16()
				self.SP = nn
			case 0x32: #LD (HL-), A
				self.mem.write(self.HL, self.AF >> 8)
				self.HL = u16(self.HL - 1)
			case 0x33: #inc SP
				self.SP = u16(self.SP + 1)
				self.mem.tick() # internal cycle
			case 0x34: #inc HL
				n = self.mem.read(self.HL)
				v = u8(n + 1)
				self.Z = v == 0
				self.N = 0
				self.H = (((n & 0xF) + 1) & 0x10) == 0x10
				self.mem.write(self.HL, v)
			case 0x35: #dec HL
				n = self.mem.read(self.HL)
				v = u8(n - 1)
				self.Z = v == 0
				self.N = 1
				self.H = (((n & 0xF) - 1) & 0x10) == 0x10
				self.mem.write(self.HL, v)
			case 0x36: # LD (HL), u8
				n = self.read_imm_u8()
				self.mem.write(self.HL, n)
			case 0x37:
				self.N = 0
				self.H = 0
				self.C = 1
			case 0x38: # JR C, e
				e = i8(self.mem.read(self.PC)); 
				self.PC = u16(self.PC + 1)
				if self.C: # cc=true
					self.PC = u16(self.PC + e)
					self.mem.tick() # internal cycle
			case 0x39: #Add HL, SP
				self.N = 0
				self.H = (((self.HL & 0xFFF) + (self.SP & 0xFFF)) & 0x1000) == 0x1000
				self.C = ((self.HL + self.SP) & 0x10000) == 0x10000
				self.HL = u16(self.HL + self.SP)
				self.mem.tick() # internal cycle
			case 0x3A: #LD A, HL-
				n = self.mem.read(self.HL)
				self.AF = (n << 8) | self.AF & 0x00FF                
				self.HL = u16(self.HL - 1)
			case 0x3B: #dec SP
				self.SP = u16(self.SP - 1)
				self.mem.tick()
			case 0x3C: #inc A
				v = u8((self.AF >> 8) + 1)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + 1) & 0x10) == 0x10
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x3D: # dec A
				v = u8((self.AF >> 8) - 1)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - (1 & 0xF)) & 0x10) == 0x10
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x3E: # LD A
				n = self.read_imm_u8()
				self.AF = self.AF & 0x00FF | (n << 8)
			case 0x3F: # CCF
				self.N = 0
				self.H = 0
				self.C = not self.C
			

			case 0x40: # LD B, B
				pass
			case 0x41: #LD B, C
				self.BC = ((self.BC & 0xFF) << 8) | (self.BC & 0x00FF)
			case 0x42: #LD B, D
				self.BC = ((self.DE >> 8) << 8) | (self.BC & 0x00FF)
			case 0x43: #LD B, E
				self.BC = ((self.DE & 0xFF) << 8) | (self.BC & 0x00FF)
			case 0x44: #LD B, H
				self.BC = ((self.HL >> 8) << 8) | (self.BC & 0x00FF)
			case 0x45: #LD B, L
				self.BC = ((self.HL & 0xFF) << 8) | (self.BC & 0x00FF)
			case 0x46: # LD B, (HL)
				n = self.mem.read(self.HL)
				self.BC = (n << 8) | (self.BC & 0x00FF)
			case 0x47: # LD B, A
				self.BC = ((self.AF >> 8) << 8) | (self.BC & 0x00FF)
			case 0x48: # LD C, B
				self.BC = (self.BC & 0xFF00) | (self.BC >> 8)
			case 0x49: # LD C, C
				pass
			case 0x4A: # LD C, D
				self.BC = (self.BC & 0xFF00) | (self.DE >> 8)
			case 0x4B: # LD C, E
				self.BC = (self.BC & 0xFF00) | (self.DE & 0xFF)
			case 0x4C: # LD C, H
				self.BC = (self.BC & 0xFF00) | (self.HL >> 8)
			case 0x4D: # LD C, L
				self.BC = (self.BC & 0xFF00) | (self.HL & 0xFF)
			case 0x4E: # LD C, (HL)
				n = self.mem.read(self.HL)
				self.BC = (self.BC & 0xFF00) | n
			case 0x4F: # LD C, A
				self.BC = (self.BC & 0xFF00) | (self.AF >> 8)

			case 0x50: # LD D, B
				self.DE = ((self.BC >> 8) << 8) | (self.DE & 0x00FF)
			case 0x51: # LD D, C
				self.DE = ((self.BC & 0xFF) << 8) | (self.DE & 0x00FF)
			case 0x52: # LD D, D
				pass
			case 0x53: # LD D, E
				self.DE = ((self.DE & 0xFF) << 8) | (self.DE & 0x00FF)
			case 0x54: # LD D, H
				self.DE = ((self.HL >> 8) << 8) | (self.DE & 0x00FF)
			case 0x55: # LD D, L
				self.DE = ((self.HL & 0xFF) << 8) | (self.DE & 0x00FF)
			case 0x56: # LD D, (HL)
				n = self.mem.read(self.HL)
				self.DE = (n << 8) | (self.DE & 0x00FF)
			case 0x57: # LD D, A
				self.DE = ((self.AF >> 8) << 8) | (self.DE & 0x00FF)
			case 0x58: # LD E, B
				self.DE = (self.DE & 0xFF00) | (self.BC >> 8)
			case 0x59: # LD E, C
				self.DE = (self.DE & 0xFF00) | (self.BC & 0xFF)
			case 0x5A: # LD E, D
				self.DE = (self.DE & 0xFF00) | (self.DE >> 8)
			case 0x5B: # LD E, E
				pass
			case 0x5C: # LD E, H
				self.DE = (self.DE & 0xFF00) | (self.HL >> 8)
			case 0x5D: # LD E, L
				self.DE = (self.DE & 0xFF00) | (self.HL & 0xFF)
			case 0x5E: # LD E, (HL)
				n = self.mem.read(self.HL)
				self.DE = (self.DE & 0xFF00) | n
			case 0x5F: # LD E, A
				self.DE = (self.DE & 0xFF00) | (self.AF >> 8)

			case 0x60: # LD, H, B
				self.HL = ((self.BC >> 8) << 8) | (self.HL & 0x00FF)
			case 0x61: # LD, H, C
				self.HL = ((self.BC & 0xFF) << 8) | (self.HL & 0x00FF)
			case 0x62: # LD, H, D
				self.HL = ((self.DE >> 8) << 8) | (self.HL & 0x00FF)
			case 0x63: # LD, H, E
				self.HL = ((self.DE & 0xFF) << 8) | (self.HL & 0x00FF)
			case 0x64: # LD, H, H
				pass
			case 0x65: # LD, H, L
				self.HL = ((self.HL & 0xFF) << 8) | (self.HL & 0x00FF)
			case 0x66: # LD, H, (HL)
				n = self.mem.read(self.HL)
				self.HL = (n << 8) | (self.HL & 0x00FF)
			case 0x67: # LD, H, A 
				self.HL = ((self.AF >> 8) << 8) | (self.HL & 0x00FF)
			case 0x68: # LD, L, B
				self.HL = (self.HL & 0xFF00) | (self.BC >> 8)
			case 0x69: # LD, L, C
				self.HL = (self.HL & 0xFF00) | (self.BC & 0xFF)
			case 0x6A:
				self.HL = (self.HL & 0xFF00) | (self.DE >> 8)
			case 0x6B: # LD, L, E
				self.HL = (self.HL & 0xFF00) | (self.DE & 0xFF)
			case 0x6C: # LD, L, H
				self.HL = (self.HL & 0xFF00) | (self.HL >> 8)
			case 0x6D:
				pass
			case 0x6E: # LD L, (HL)
				n = self.mem.read(self.HL)
				self.HL = (self.HL & 0xFF00) | n
			case 0x6F: #LD, L, A 
				self.HL = (self.HL & 0xFF00) | (self.AF >> 8)

			case 0x70: # LD (HL), B
				self.mem.write(self.HL, self.BC >> 8)
			case 0x71: # LD (HL), C
				self.mem.write(self.HL, self.BC & 0xFF)
			case 0x72: # LD (HL), D
				self.mem.write(self.HL, self.DE >> 8)
			case 0x73: # LD (HL), E
				self.mem.write(self.HL, self.DE & 0xFF)
			case 0x74: # LD (HL), H
				self.mem.write(self.HL, self.HL >> 8)
			case 0x75: # LD (HL), L
				self.mem.write(self.HL, self.HL & 0xFF)
			case 0x76:
				#HALT
				exit(1)
			case 0x77: # LD (HL), A
				self.mem.write(self.HL, self.AF >> 8)
			case 0x78: # LD A, B
				self.AF = (self.AF & 0x00FF) | ((self.BC >> 8) << 8)
			case 0x79: # LD A, C
				self.AF = ((self.BC & 0xFF) << 8) | (self.AF & 0x00FF)
			case 0x7A: # LD A, D
				self.AF = (self.AF & 0x00FF) | ((self.DE >> 8) << 8)
			case 0x7B: # LD A, E
				self.AF = ((self.DE & 0xFF) << 8) | (self.AF & 0x00FF)
			case 0x7C: # LD A, H
				self.AF = (self.AF & 0x00FF) | ((self.HL >> 8) << 8)
			case 0x7D: # LD A, L
				self.AF = ((self.HL & 0xFF) << 8) | (self.AF & 0x00FF)
			case 0x7E: # LD, A, (HL)
				n = self.mem.read(self.HL)
				self.AF = (n << 8) | (self.AF & 0x00FF)
			case 0x7F: # LD, A, A
				pass

			case 0x80: # ADD A, B
				v = u8((self.AF >> 8) + (self.BC >> 8))
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + ((self.BC >> 8) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.BC >> 8)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x81: # ADD A, C
				v = u8((self.AF >> 8) + (self.BC & 0xFF))
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + ((self.BC & 0xFF) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.BC & 0xFF)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x82: # ADD A, D
				v = u8((self.AF >> 8) + (self.DE >> 8))
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + ((self.DE >> 8) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.DE >> 8)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x83: # ADD A, E
				v = u8((self.AF >> 8) + (self.DE & 0xFF))
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + ((self.DE & 0xFF) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.DE & 0xFF)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x84: # ADD A, H
				v = u8((self.AF >> 8) + (self.HL >> 8))
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + ((self.HL >> 8) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.HL >> 8)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x85: # ADD A, L
				v = u8((self.AF >> 8) + (self.HL & 0xFF))
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + ((self.HL & 0xFF) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.HL & 0xFF)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x86: # ADD A, (HL)
				n = self.mem.read(self.HL)
				v = u8((self.AF >> 8) + n)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + (n & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + n) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x87: # ADD A, A
				v = u8((self.AF >> 8) + (self.AF >> 8))
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + ((self.AF >> 8) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.AF >> 8)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x88: # ADC A, B
				v = u8((self.AF >> 8) + (self.BC >> 8) + self.C)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + ((self.BC >> 8) & 0xF) + self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.BC >> 8) + self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x89: # ADC A, C
				v = u8((self.AF >> 8) + (self.BC & 0xFF) + self.C)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + (self.BC & 0xF) + self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.BC & 0xFF) + self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x8A: # ADC A, D
				v = u8((self.AF >> 8) + (self.DE >> 8) + self.C)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + ((self.DE >> 8) & 0xF) + self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.DE >> 8) + self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x8B: # ADC A, E
				v = u8((self.AF >> 8) + (self.DE & 0xFF) + self.C)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + (self.DE & 0xF) + self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.DE & 0xFF) + self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x8C: # ADC A, H
				v = u8((self.AF >> 8) + (self.HL >> 8) + self.C)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + ((self.HL >> 8) & 0xF) + self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.HL >> 8) + self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x8D: # ADC A, L
				v = u8((self.AF >> 8) + (self.HL & 0xFF) + self.C)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + (self.HL & 0xF) + self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.HL & 0xFF) + self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x8E: # ADC A, (HL)
				n = self.mem.read(self.HL)
				v = u8((self.AF >> 8) + n + self.C)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + (n & 0xF) + self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + n + self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x8F: # ADC A, A
				v = u8((self.AF >> 8) + (self.AF >> 8) + self.C)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + ((self.AF >> 8) & 0xF) + self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + (self.AF >> 8) + self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)

			case 0x90: # SUB A, B
				v = u8((self.AF >> 8) - (self.BC >> 8))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.BC >> 8) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.BC >> 8)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x91: # SUB A, C
				v = u8((self.AF >> 8) - (self.BC & 0xFF))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.BC & 0xFF) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.BC & 0xFF)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x92: # SUB A, D
				v = u8((self.AF >> 8) - (self.DE >> 8))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.DE >> 8) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.DE >> 8)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x93: # SUB A, E
				v = u8((self.AF >> 8) - (self.DE & 0xFF))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.DE & 0xFF) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.DE & 0xFF)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x94: # SUB A, H
				v = u8((self.AF >> 8) - (self.HL >> 8))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.HL >> 8) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.HL >> 8)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x95: # SUB A, L
				v = u8((self.AF >> 8) - (self.HL & 0xFF))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.HL & 0xFF) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.HL & 0xFF)) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x96: # SUB A, (HL)
				n = self.mem.read(self.HL)
				v = u8((self.AF >> 8) - n)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - (n & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - n) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x97: # SUB A, A
				self.AF = self.AF & 0x00FF
				self.Z = 1
				self.N = 1
				self.H = 0
				self.C = 0
			case 0x98: # SBC A, B
				v = u8((self.AF >> 8) - (self.BC >> 8) - self.C)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.BC >> 8) & 0xF) - self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.BC >> 8) - self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x99: # SBC A, C
				v = u8((self.AF >> 8) - (self.BC & 0xFF) - self.C)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.BC & 0xFF) & 0xF) - self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.BC & 0xFF) - self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x9A: # SBC A, D
				v = u8((self.AF >> 8) - (self.DE >> 8) - self.C)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.DE >> 8) & 0xF) - self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.DE >> 8) - self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x9B: # SBC A, E
				v = u8((self.AF >> 8) - (self.DE & 0xFF) - self.C)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.DE & 0xFF) & 0xF) - self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.DE & 0xFF) - self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x9C: # SBC A, H
				v = u8((self.AF >> 8) - (self.HL >> 8) - self.C)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.HL >> 8) & 0xF) - self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.HL >> 8) - self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x9D: # SBC A, L
				v = u8((self.AF >> 8) - (self.HL & 0xFF) - self.C)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.HL & 0xFF) & 0xF) - self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.HL & 0xFF) - self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x9E: # SBC A, (HL)
				n = self.mem.read(self.HL)
				v = u8((self.AF >> 8) - n - self.C)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - (n & 0xF) - self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - n - self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0x9F: # SBC A, A
				v = u8((self.AF >> 8) - (self.AF >> 8) - self.C)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.AF >> 8) & 0xF) - self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.AF >> 8) - self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)

			case 0xA0: # AND A, B
				v = ((self.AF >> 8) & (self.BC >> 8))
				self.AF = (v << 8) | (self.AF & 0x00FF)
				self.Z = v == 0
				self.N = 0
				self.H = 1
				self.C = 0
			case 0xA1: # AND A, C
				v = ((self.AF >> 8) & (self.BC & 0xFF))
				self.AF = (v << 8) | (self.AF & 0x00FF)
				self.Z = v == 0
				self.N = 0
				self.H = 1
				self.C = 0
			case 0xA2: # AND A, D
				v = ((self.AF >> 8) & (self.DE >> 8))
				self.AF = (v << 8) | (self.AF & 0x00FF)
				self.Z = v == 0
				self.N = 0
				self.H = 1
				self.C = 0
			case 0xA3: # AND A, E
				v = ((self.AF >> 8) & (self.DE & 0xFF))
				self.AF = (v << 8) | (self.AF & 0x00FF)
				self.Z = v == 0
				self.N = 0
				self.H = 1
				self.C = 0
			case 0xA4: # AND A, H
				v = ((self.AF >> 8) & (self.HL >> 8))
				self.AF = (v << 8) | (self.AF & 0x00FF)
				self.Z = v == 0
				self.N = 0
				self.H = 1
				self.C = 0
			case 0xA5: # AND A, L
				v = ((self.AF >> 8) & (self.HL & 0xFF))
				self.AF = (v << 8) | (self.AF & 0x00FF)
				self.Z = v == 0
				self.N = 0
				self.H = 1
				self.C = 0
			case 0xA6: # AND A, HL
				n = self.mem.read(self.HL)
				v = ((self.AF >> 8) & n)
				self.AF = (v << 8) | (self.AF & 0x00FF)
				self.Z = v == 0
				self.N = 0
				self.H = 1
				self.C = 0
			case 0xA7: # AND A, A
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 1
				self.C = 0
			case 0xA8: # XOR A, B
				self.AF = (((self.AF >> 8) ^ (self.BC >> 8)) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xA9: # XOR A, B
				self.AF = (((self.AF >> 8) ^ (self.BC & 0xFF)) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xAA: # XOR A, D
				self.AF = (((self.AF >> 8) ^ (self.DE >> 8)) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xAB: # XOR A, E
				self.AF = (((self.AF >> 8) ^ (self.DE & 0xFF)) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xAC: # XOR A, H
				self.AF = (((self.AF >> 8) ^ (self.HL >> 8)) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xAD: # XOR A, L
				self.AF = (((self.AF >> 8) ^ (self.HL & 0xFF)) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xAE: # XOR A, (HL)
				n = self.mem.read(self.HL)
				v = (self.AF >> 8) ^ n
				self.AF = (v << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xAF: # XOR A, A
				self.AF = self.AF & 0x00FF
				self.Z = 1
				self.N = 0
				self.H = 0
				self.C = 0

			case 0xB0: # OR A, B
				self.AF |= ((self.BC >> 8) << 8)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xB1: # OR A, C
				self.AF |= ((self.BC & 0xFF) << 8)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xB2: # OR A, D
				self.AF |= ((self.DE >> 8) << 8)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xB3: # OR A, E
				self.AF |= ((self.DE & 0xFF) << 8)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xB4: # OR A, H
				self.AF |= ((self.HL >> 8) << 8)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xB5: # OR A, L
				self.AF |= ((self.HL & 0xFF) << 8)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xB6: # OR, A, (HL)
				v = self.mem.read(self.HL)
				self.AF |= (v << 8)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xB7: # OR A, A
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xB8: # CP A, B
				v = u8((self.AF >> 8) - (self.BC >> 8))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.BC >> 8) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.BC >> 8)) & 0x100) == 0x100
			case 0xB9: # CP A, C
				v = u8((self.AF >> 8) - (self.BC & 0xFF))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.BC & 0xFF) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.BC & 0xFF)) & 0x100) == 0x100
			case 0xBA: # CP A, D
				v = u8((self.AF >> 8) - (self.DE >> 8))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.DE >> 8) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.DE >> 8)) & 0x100) == 0x100
			case 0xBB: # CP A, E
				v = u8((self.AF >> 8) - (self.DE & 0xFF))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.DE & 0xFF) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.DE & 0xFF)) & 0x100) == 0x100
			case 0xBC: # CP A, H
				v = u8((self.AF >> 8) - (self.HL >> 8))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.HL >> 8) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.HL >> 8)) & 0x100) == 0x100
			case 0xBD: # CP A, L
				v = u8((self.AF >> 8) - (self.HL & 0xFF))
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - ((self.HL & 0xFF) & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - (self.HL & 0xFF)) & 0x100) == 0x100
			case 0xBE:
				n = self.mem.read(self.HL)
				v = u8((self.AF >> 8) - n)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - (n & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - n) & 0x100) == 0x100
			case 0xBF: # CP A, A
				self.Z = 1
				self.N = 1
				self.H = 0
				self.C = 0

			case 0xC0: # RET NZ
				self.mem.tick() # internal cycle
				if not self.Z:
					lsb = self.mem.read(self.SP)
					self.SP = u16(self.SP + 1)
					msb = self.mem.read(self.SP)
					self.SP = u16(self.SP + 1)
					self.PC = (msb << 8) | lsb
					self.mem.tick() # internal cycle
			case 0xC1: # POP BC
				lsb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				msb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				self.BC = (msb << 8) | lsb
			case 0xC2: # JP NZ, nn
				nn = self.read_imm_u16()
				if (not self.Z):
					self.PC = nn
					self.mem.tick() # internal cycle
			case 0xC3: # JP nn
				nn = self.read_imm_u16()
				self.PC = nn
				self.mem.tick()
			case 0xC4: # CALL NZ, nn
				nn = self.read_imm_u16()
				if (not self.Z):
					self.mem.tick() # internal cycle
					self.SP = u16(self.SP - 1)
					self.mem.write(self.SP, self.PC >> 8)
					self.SP = u16(self.SP - 1)
					self.mem.write(self.SP, self.PC & 0xFF)
					self.PC = nn
			case 0xC5: # PUSH BC
				self.mem.tick()
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.BC >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.BC & 0xFF)
			case 0xC6: # ADD A, n
				n = self.read_imm_u8()
				v = u8((self.AF >> 8) + n)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + (n & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + n) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0xC7: # RST 00h
				self.mem.tick() # internal cycle
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC & 0xFF)
				self.PC = 0
			case 0xC8: # RET Z
				self.mem.tick() # internal cycle
				if self.Z:
					lsb = self.mem.read(self.SP)
					self.SP = u16(self.SP + 1)
					msb = self.mem.read(self.SP)
					self.SP = u16(self.SP + 1)
					self.PC = (msb << 8) | lsb
					self.mem.tick() # internal cycle
			case 0xC9: # RET
				lsb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				msb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				self.PC = (msb << 8) | lsb
				self.mem.tick()
			case 0xCA: #JP Z, nn
				nn = self.read_imm_u16()
				if (self.Z):
					self.PC = nn 
					self.mem.tick() # internal cycle
			case 0xCC: # CALL Z, nn
				nn = self.read_imm_u16()
				if (self.Z):
					self.mem.tick() # internal cycle
					self.SP = u16(self.SP - 1)
					self.mem.write(self.SP, self.PC >> 8)
					self.SP = u16(self.SP - 1)
					self.mem.write(self.SP, self.PC & 0xFF)
					self.PC = nn
			case 0xCD: # CALL nn
				nn = self.read_imm_u16()
				self.mem.tick()
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC & 0xFF)
				self.PC = nn
			case 0xCE: # ADC n
				n = self.read_imm_u8()
				v = u8((self.AF >> 8) + n + self.C)
				self.Z = v == 0
				self.N = 0
				self.H = ((((self.AF >> 8) & 0xF) + (n & 0xF) + self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) + n + self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0xCF: # RST 08h
				self.mem.tick() # internal cycle
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC & 0xFF)
				self.PC = 0x08

			case 0xD0: # RET NC
				self.mem.tick() # internal cycle
				if not self.C:
					lsb = self.mem.read(self.SP)
					self.SP = u16(self.SP + 1)
					msb = self.mem.read(self.SP)
					self.SP = u16(self.SP + 1)
					self.PC = (msb << 8) | lsb
					self.mem.tick() # internal cycle
			case 0xD1: # POP DE
				lsb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				msb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				self.DE = (msb << 8) | lsb
			case 0xD2: # JP NC, nn
				nn = self.read_imm_u16()
				if (not self.C):
					self.PC = nn
					self.mem.tick() # internal cycle
			case 0xD4: # CALL NC, nn
				nn = self.read_imm_u16()
				if (not self.C):
					self.mem.tick() # internal cycle
					self.SP = u16(self.SP - 1)
					self.mem.write(self.SP, self.PC >> 8)
					self.SP = u16(self.SP - 1)
					self.mem.write(self.SP, self.PC & 0xFF)
					self.PC = nn
			case 0xD5: # PUSH DE
				self.mem.tick()
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.DE >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.DE & 0xFF)
			case 0xD6: # SUB A, n
				n = self.read_imm_u8()
				v = u8((self.AF >> 8) - n)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - (n & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - n) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0xD7: # RST 10h
				self.mem.tick() # internal cycle
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC & 0xFF)
				self.PC = 0x10
			case 0xD8: # RET C
				self.mem.tick() # internal cycle
				if self.C:
					lsb = self.mem.read(self.SP)
					self.SP = u16(self.SP + 1)
					msb = self.mem.read(self.SP)
					self.SP = u16(self.SP + 1)
					self.PC = (msb << 8) | lsb
					self.mem.tick() # internal cycle
			case 0xD9: # RETI
				lsb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				msb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				self.PC = (msb << 8) | lsb
				self.ime = 1
				self.mem.tick() # internal cycle
			case 0xDA: #JP C, nn
				nn = self.read_imm_u16()
				if (self.C):
					self.PC = nn 
					self.mem.tick() # internal cycle
			case 0xDC: # CALL C, nn
				nn = self.read_imm_u16()
				if (self.C):
					self.mem.tick() # internal cycle
					self.SP = u16(self.SP - 1)
					self.mem.write(self.SP, self.PC >> 8)
					self.SP = u16(self.SP - 1)
					self.mem.write(self.SP, self.PC & 0xFF)
					self.PC = nn
			case 0xDE: # SBC n
				n = self.read_imm_u8()
				v = u8((self.AF >> 8) - n - self.C)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - (n & 0xF) - self.C) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - n - self.C) & 0x100) == 0x100
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0xDF: # RST 18h
				self.mem.tick() # internal cycle
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC & 0xFF)
				self.PC = 0x18
			
			case 0xE0: # LDH (n), A
				n = self.read_imm_u8()
				self.mem.write(0xFF00 | n, (self.AF >> 8))
			case 0xE1: # POP HL
				lsb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				msb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				self.HL = (msb << 8) | lsb
			case 0xE2:# LD (FF00+C), A
				self.mem.write(0xFF00 | (self.BC & 0xFF), self.AF >> 8)
			case 0xE5: # PUSH HL
				self.mem.tick()
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.HL >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.HL & 0xFF)
			case 0xE6: # AND n
				n = self.read_imm_u8()
				self.AF &= (n << 8) | 0xFF
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 1
				self.C = 0
			case 0xE7: # RST 20h
				self.mem.tick() # internal cycle
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC & 0xFF)
				self.PC = 0x20
			case 0xE8: # ADD SP, i8, make a note
				e = i8(self.read_imm_u8())
				self.Z = 0
				self.N = 0
				self.H = (((self.SP & 0xF) + (e & 0xF)) & 0x10) == 0x10
				self.C = (((self.SP & 0xFF) + (e & 0xFF)) & 0x100) == 0x100
				self.SP = u16(self.SP + e)
				self.mem.tick() # internal cycle
				self.mem.tick() # SP write internal cycle (?)
			case 0xE9: # JP HL
				self.PC = self.HL
			case 0xEA: # LD (nn), A
				nn = self.read_imm_u16()
				self.mem.write(nn, (self.AF >> 8))
			case 0xEE: # XOR A, n
				n = self.read_imm_u8()
				self.AF = (((self.AF >> 8) ^ n) << 8) | (self.AF & 0x00FF)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xEF: # RST 28h
				self.mem.tick() # internal cycle
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC & 0xFF)
				self.PC = 0x28

			case 0xF0: # LDH A, (n)
				n = self.read_imm_u8()
				self.AF = (self.AF & 0x00FF) | (self.mem.read(0xFF00 | n) << 8)
			case 0xF1: # POP AF
				lsb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				msb = self.mem.read(self.SP)
				self.SP = u16(self.SP + 1)
				self.Z = (lsb >> 7) & 1
				self.N = (lsb >> 6) & 1
				self.H = (lsb >> 5) & 1
				self.C = (lsb >> 4) & 1
				self.AF = (msb << 8) | self.flag_bits()
			case 0xF2: # LD A, (FF00+C)
				v = self.mem.read(0xFF00 | (self.BC & 0xFF))
				self.AF = (v << 8) | (self.AF & 0x00FF)
			case 0xF3: # DI
				self.ime = 0
			case 0xF5: # PUSH AF
				self.mem.tick() # internal cycle
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.AF >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.flag_bits() | (self.AF & 0x0F))
			case 0xF6: # OR n
				n = self.read_imm_u8()
				self.AF |= (n << 8)
				self.Z = (self.AF >> 8) == 0
				self.N = 0
				self.H = 0
				self.C = 0
			case 0xF7: # RST 30h
				self.mem.tick() # internal cycle
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC & 0xFF)
				self.PC = 0x30
			case 0xF8: # LD HL, SP+i8
				e = i8(self.read_imm_u8())
				self.HL = u16(self.SP + e)
				self.Z = 0
				self.N = 0
				self.H = (((self.SP & 0xF) + (e & 0xF)) & 0x10) == 0x10
				self.C = (((self.SP & 0xFF) + (e & 0xFF)) & 0x100) == 0x100
				self.mem.tick() # internal cycle
			case 0xF9: # LD SP, HL
				self.SP = self.HL
				self.mem.tick() # internal cycle
			case 0xFA: # LD A, (nn)
				nn = self.read_imm_u16()
				self.AF = (self.AF & 0x00FF) | (self.mem.read(nn) << 8)
			case 0xFB: # EI
				self.delayed_ime_enable = True
			case 0xFE: # CP A, n
				n = self.read_imm_u8()
				v = u8((self.AF >> 8) - n)
				self.Z = v == 0
				self.N = 1
				self.H = ((((self.AF >> 8) & 0xF) - (n & 0xF)) & 0x10) == 0x10
				self.C = (((self.AF >> 8) - n) & 0x100) == 0x100
			case 0xFF: # RST 38h
				self.mem.tick() # internal cycle
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC >> 8)
				self.SP = u16(self.SP - 1)
				self.mem.write(self.SP, self.PC & 0xFF)
				self.PC = 0x38

			case _:
				print("no code :(")
				exit(1)
		