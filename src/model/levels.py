class Level:
    def __init__(self, name, elevation):
        self.name = name
        self.elevation = elevation

class Building:
    def __init__(self):
        # Niveles por defecto
        self.levels = [
            Level("Cimentación", 0.0),
            Level("Planta 1", 3.0),
            Level("Planta 2", 6.0)
        ]
        self.active_level_index = 1 # Empezamos en Planta 1
        
    def get_active_level(self):
        return self.levels[self.active_level_index]
        
    def set_active_level(self, index):
        if 0 <= index < len(self.levels):
            self.active_level_index = index
            
    def get_foundation_level(self):
        return self.levels[0]
