
from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'VWAP Low Rolling Method: Junior Trader Manual', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_manual():
    pdf = PDF()
    pdf.add_page()
    
    # Fonts
    pdf.set_font("Arial", size=11)
    
    body = """
Objective: Capture intraday trends by shorting straddles (CE+PE) with a dynamic "Rolling" filter that adapts to market volatility.

---

1. Daily Setup (09:15 - 09:32)
Status: PRE-MARKET / OBSERVATION.

A. Initial Spot Check (09:32 AM):
   - At exactly 09:32 AM, check the Nifty Spot Price.
   - Round to the nearest 50 to select your Initial ATM Strike.
   - Example: Spot 24110 -> 24100 Straddle.
   - DO NOT ENTER YET. Wait for confirmation.

B. Trading Start (09:32 AM):
   - Loading Charts: Load the Straddle Chart.
   - Add VWAP Indicator.
   - Start monitoring for Entry Signals IMMEDIATELY from 09:32.

---

2. Entry Logic (The Filter)
Window: 09:32 AM to 10:02 AM (30 Minutes)

Signal: "Breakdown Confirmation"
   - Monitor the Straddle Chart (1-minute candles).
   - Reference Level: The Lowest Low of the last 3 candles (Group A).
   - Trigger (Group B): 
     1. Candle Close < Reference Level
     2. Candle Close < VWAP
   
   Action: SELL (Short) the Straddle at Market Price.
   Stop Loss: High of Group A + Buffer (Min 10, Max 20 pts).

---

3. Position Management (The "Ratchet")

A. Stop Loss (SL) Hit:
   - If Price >= SL -> EXIT IMMEDIATELY.
   - *CRITICAL UPDATE*: Upon SL Hit, the "Filter" updates.
   - New Filter Level = The Lowest Low of the day (since 09:16) for this straddle.
   - Re-Entry: Only allowed if price breaks BELOW this new, lower level.

B. Trailing SL (Locking Profit):
   - If Profit >= +20 pts -> Move SL to Cost.
   - For every +10 pts further profit -> Move SL down by 10 pts.

C. Portfolio Risk:
   - Max Daily Loss: 70 Points.
   - If accumulated loss hits -70 pts -> STOP TRADING for the day.

---

4. Rolling Logic (Strike Shift)
Trigger: Nifty Spot moves +/- 100 Points away from your current Strike.

Action:
   1. CLOSE current position (if any).
   2. Select NEW ATM Strike (based on current Spot).
   3. Reset Data:
      - Load Chart for NEW Strike.
      - *CRITICAL*: The "Filter Level" for the new strike is set to its Lowest Low (from 09:16 to Now).
      - You can only enter the new strike if it breaks this historical low.

---

Summary of Key Times:
- 09:32 AM: Check Spot, Pick Strike, Start Trading.
- 10:02 AM: Entry Window Closes (unless SL hit extends it).
- 15:20 PM: Intraday square-off.

"""
    # Fix encoding
    body = body.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, body)
    
    filename = "Junior_Trader_Manual_Rolling.pdf"
    pdf.output(filename)
    print(f"Manual created: {filename}")

if __name__ == "__main__":
    create_manual()
