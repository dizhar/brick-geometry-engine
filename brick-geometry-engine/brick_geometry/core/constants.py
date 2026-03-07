# LEGO Drawing Units (LDU) — the canonical unit in LDraw format
# 1 LDU = 0.4 mm

# --- Unit conversions ---
LDU_TO_MM: float = 0.4
MM_TO_LDU: float = 1.0 / LDU_TO_MM          # 2.5 LDU per mm

# --- Stud grid ---
STUD_SPACING_LDU: int = 20                   # centre-to-centre stud spacing (8 mm)
STUD_DIAMETER_LDU: float = 12.0              # outer stud diameter (4.8 mm)
STUD_HEIGHT_LDU: float = 4.0                 # stud protrusion above top face (1.6 mm)

# --- Anti-stud (tube) ---
ANTI_STUD_DIAMETER_LDU: float = 10.8        # inner tube diameter (4.32 mm)

# --- Part heights ---
PLATE_HEIGHT_LDU: int = 8                    # 1 plate = 3.2 mm
BRICK_HEIGHT_LDU: int = 24                   # 1 brick = 9.6 mm  (= 3 plates)

# --- Tolerance ---
POSITION_TOLERANCE_LDU: float = 0.01        # floating-point comparison threshold
