
from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'VWAP Straddle Strategy: Junior Trader Manual', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf():
    pdf = PDF()
    pdf.add_page()
    
    # Title Content
    pdf.set_font("Arial", size=11)
    
    body = """
Objective: Capture intraday trends by shorting straddles (CE+PE) when price breaks a calculated support level (Reference Low).

---

1. Daily Setup (09:15 - 09:34)
Status: OBSERVATION ONLY. NO TRADES.

A. Initial ATM Strike Selection (09:34):
   - Wait until 09:34 AM.
   - Note Nifty Spot Price.
   - Round to nearest 50 -> ATM Strike.
   - Example: Spot 25772 -> Strike 25750.

B. Load Charts:
   - Load Straddle Chart (ATM CE + ATM PE).
   - Add VWAP Indicator.

---

2. Entry Logic (The Breakdown)
Window: 09:34 AM to 10:04 AM (Updated: 30 mins)

Core Concept: Rolling 6-Minute Pattern. Reference Line moves with time.

A. Define the Groups (Dynamic):
   For any "Current Time" (e.g., 09:34):
   - Group B (Live): The current 3 one-minute candles (09:32, 09:33, 09:34).
   - Group A (Setup): The PREVIOUS 3 one-minute candles (09:29, 09:30, 09:31).

B. Establish Reference Line:
   - Look at Group A.
   - Find the Lowest Low among these 3 candles.
   - This = Reference Line.

C. Trigger Condition:
   - Monitor Group B.
   - Condition 1: Straddle Price < VWAP.
   - Condition 2: Candle MUST CLOSE BELOW Reference Line.
   - Action: ENTER TRADE (SHORT STRADDLE).

Example at 09:45:
   - Trigger: Close of 09:45 candle < Lowest Low of (09:40-09:42).

Important: If price touches but closes above, DO NOT ENTER.

---

3. Position Management

Stop Loss (SL):
   - Set 10-20 points above Entry Price.
   - Logic: Max High of Group A - Entry Price (Clamped 10-20pts).

Trailing SL (Locking Profits):
   - At +20 pts Profit -> Move SL to Cost.
   - Every +10 pts Profit thereafter -> Move SL down by 10 pts.

Portfolio Stop Loss (Daily Risk Cap):
   - Max Loss: 70 Points per day.
   - If reached, STOP TRADING for the day.

EOD Exit:
   - Close manually at 15:20 PM if SL not hit.

---

4. Rolling Rules (Strike Shift)
Active FROM: 09:34 AM (Do not roll early!)

Trigger: Assymetric Spot Move (+/- 80 points).
   - Spot > Strike + 80 OR Spot < Strike - 80.
   - Condition: Must NOT be in an active trade.

Action:
   - Abandon old strike.
   - Select NEW ATM Strike.
   - Reset Reference Line: Lowest Low of NEW straddle (09:16 to Current Time).

---

5. Re-Entry Logic
   - If SL hit: Entry Window re-opens for 20 mins from Exit Time.
   - Logic: Same conditions (Close < Reference Line).

---

6. Checklist
   [ ] Time > 09:34
   [ ] Spot determined Correct ATM
   [ ] Straddle < VWAP
   [ ] Candle Closed < Reference Low
   [ ] Inside Active Window
"""
    
    # Simple markdown-ish parsing
    for line in body.split('\n'):
        line = line.strip()
        if not line:
            pdf.ln(5)
            continue
            
        if line.startswith("---"):
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            continue
            
        if line[0].isdigit() and "." in line[:3]:
            # Header
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 0, 128)
            pdf.cell(0, 10, line, 0, 1)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", size=11)
        elif line.startswith("Status:") or line.startswith("Window:") or line.startswith("Active FROM:"):
             pdf.set_font("Arial", 'I', 10)
             pdf.cell(0, 6, line, 0, 1)
             pdf.set_font("Arial", size=11)
        elif line.startswith("-") or line.startswith("["):
            pdf.set_x(15) # Indent
            pdf.multi_cell(0, 6, line)
        else:
            pdf.multi_cell(0, 6, line)

    output_path = os.path.join("c:\\Users\\Rosario\\.gemini\\antigravity\\brain\\ea2ec81b-438b-4e41-af99-bed5df5ef91d", "Junior_Trader_Manual_v4.pdf")
    pdf.output(output_path)
    print(f"PDF created at: {output_path}")

if __name__ == "__main__":
    create_pdf()
