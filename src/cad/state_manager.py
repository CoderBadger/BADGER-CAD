from enum import Enum

class CadMode(Enum):
    SELECCION = 1
    DIBUJAR_PILAR = 2
    DIBUJAR_VIGA = 3
    ASIGNAR_LOSA = 4

class StateManager:
    def __init__(self):
        self.current_mode = CadMode.SELECCION
        # Almacena el estado de clics, por ejemplo, para vigas (necesita 2 clics)
        self.click_state = []
        self.observers = []
        
    def set_mode(self, mode: CadMode):
        self.current_mode = mode
        self.click_state = []
        self._notify()
        
    def add_observer(self, callback):
        self.observers.append(callback)
        
    def _notify(self):
        for obs in self.observers:
            obs(self.current_mode)
