import unittest
import json
from os import listdir
from cpu import CPU 

class TestCPUOps(unittest.TestCase):
    def initialize_registers(self, cpu: CPU, initial):
        cpu.table.PC = initial["pc"]
        cpu.table.SP = initial["sp"]
        cpu.table.AF = (initial["a"] << 8) | (initial["f"] & 0x0F)
        cpu.table.BC = (initial["b"] << 8) | (initial["c"] & 0xFF)
        cpu.table.DE = (initial["d"] << 8) | (initial["e"] & 0xFF)
        cpu.table.HL = (initial["h"] << 8) | (initial["l"] & 0xFF)

        cpu.table.Z = (initial["f"] >> 7) & 1
        cpu.table.N = (initial["f"] >> 6) & 1
        cpu.table.H = (initial["f"] >> 5) & 1
        cpu.table.C = (initial["f"] >> 4) & 1

        for item in initial["ram"]:
            cpu.mem.memory[item[0]] = item[1]

    def test_jsmooSM83(self):
        cpu = CPU(None)

        for test_filename in listdir("sm83_tests_CB"):
            with open(f'sm83_tests_CB/{test_filename}') as json_file:
                opcode_tests = json.load(json_file)
                for test in opcode_tests:
                    self.initialize_registers(cpu, test["initial"])
                    cpu.execute()

                    final = test["final"]

                    self.assertEqual(final["a"], cpu.table.AF >> 8)
                    self.assertEqual(final["f"], cpu.table.flag_bits() | (cpu.table.AF & 0x0F))
                    self.assertEqual(final["b"], cpu.table.BC >> 8)
                    self.assertEqual(final["c"], cpu.table.BC & 0xFF)
                    self.assertEqual(final["d"], cpu.table.DE >> 8)
                    self.assertEqual(final["e"], cpu.table.DE & 0xFF)
                    self.assertEqual(final["h"], cpu.table.HL >> 8)
                    self.assertEqual(final["l"], cpu.table.HL & 0xFF)
                    self.assertEqual(final["pc"], cpu.table.PC)
                    self.assertEqual(final["sp"], cpu.table.SP)
                    
                    for item in final["ram"]:
                        self.assertEqual(cpu.mem.memory[item[0]], item[1])

                    self.assertEqual(len(test["cycles"]), cpu.mem.ticks_per_instr)
                    cpu.mem.ticks_per_instr = 0

unittest.main()

'''
load test .json;
for test in test.json:
    set initial processor state from test;
    set initial RAM state from test;
    
    for cycle in test:
        cycle processor
        if we are checking cycle-by-cycle:
            compare our R/W/MRQ/Address/Data pins against the current cycle;
      
    compare final RAM state to test and report any errors;
    compare final processor state to test and report any errors;
'''