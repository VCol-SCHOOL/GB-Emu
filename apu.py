class APU:
    def __init__(self):
        self.NR52 = 0x0 # Audio master control
        self.NR51 = 0x0 # Sound panning
        self.NR50 = 0x0 # Master volume & VIN panning

    def tick(self):
        pass