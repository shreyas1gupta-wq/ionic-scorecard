import pandas as pd, numpy as np
SC="C:/Users/SHREYA~1.1GU/AppData/Local/Temp/claude/c--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500/0c22b4db-aef8-438e-81af-b9cb0af5930c/scratchpad"
c=pd.read_csv(f"{SC}/cycles.csv")
c=c.dropna(subset=['spot_ent','spot_exp']).copy()
c['entry']=pd.to_datetime(c['entry']); c['expiry']=pd.to_datetime(c['expiry'])
n=len(c)
print(f"monthly cycles with spot: {n}  window {c['entry'].min().date()}..{c['expiry'].max().date()}")
# ---- FILL AUDIT ----
ce_fill=c['Kc'].notna().sum(); collar_fill=(c['Kc'].notna()&c['Kp'].notna()).sum()
print(f"\n== FILL AUDIT (5% OTM band [1.03-1.08] / [0.92-0.97], entry ~27-34 DTE, vol>0) ==")
print(f"OS-22 covered-call CE fillable cycles: {ce_fill}/{n} = {ce_fill/n:.0%}")
print(f"OS-23 collar (needs CE & PE) fillable cycles: {collar_fill}/{n} = {collar_fill/n:.0%}")
print(f"cycles where NO CE traded at all on entry day (data gap): {(c['n_ce']==0).sum()}/{n}")
# ---- DETERMINISTIC OVERLAY ECONOMICS from spot (no option fill needed) ----
c['ret_pct']=100*(c['spot_exp']-c['spot_ent'])/c['spot_ent']
Kc=1.05*c['spot_ent']; Kp=0.95*c['spot_ent']
c['cap_loss_pts']=np.maximum(c['spot_exp']-Kc,0.0)          # upside given up by short 5% call
c['cap_loss_pct']=100*c['cap_loss_pts']/c['spot_ent']
c['put_pay_pts']=np.maximum(Kp-c['spot_exp'],0.0)           # protection paid by long 5% put
c['put_pay_pct']=100*c['put_pay_pts']/c['spot_ent']
print(f"\n== NIFTY ~1-month hold return distribution (n={n}) ==")
print(f"mean={c['ret_pct'].mean():+.2f}%  median={c['ret_pct'].median():+.2f}%  std={c['ret_pct'].std():.2f}%  min={c['ret_pct'].min():+.2f}%  max={c['ret_pct'].max():+.2f}%")
print(f"months up>5% (call cap bites): {(c['ret_pct']>5).sum()}/{n} = {(c['ret_pct']>5).mean():.0%}")
print(f"months down>5% (put protects): {(c['ret_pct']<-5).sum()}/{n} = {(c['ret_pct']<-5).mean():.0%}")
print(f"\n== OS-22 covered-call CAP DRAG (deterministic, pre-premium) ==")
print(f"mean upside GIVEN UP: {c['cap_loss_pct'].mean():.3f}%/mo of spot ({c['cap_loss_pts'].mean():.0f} pts)  | worst {c['cap_loss_pct'].max():.2f}%")
print(f"cumulative upside given up over {n} cycles: {c['cap_loss_pct'].sum():.1f}% of spot")
print(f"  breakeven premium needed just to offset cap = {c['cap_loss_pct'].mean():.3f}%/mo; single observed 5%OTM CE premium = 0.13% spot (Feb-2026, VIX~12)")
print(f"\n== OS-23 collar PUT-COST side (deterministic) ==")
print(f"mean protection RECEIVED from long put: {c['put_pay_pct'].mean():.3f}%/mo ({c['put_pay_pts'].mean():.0f} pts)")
print(f"cumulative protection over window: {c['put_pay_pct'].sum():.1f}% of spot  (put mostly expires worthless in this bull tape)")
# regime split
pre=c[c['expiry']<'2025-09-01']; post=c[c['expiry']>='2025-09-01']
print(f"\n== REGIME (Sept-2025 break) NIFTY monthly ret mean: pre={pre['ret_pct'].mean():+.2f}% (n={len(pre)})  post={post['ret_pct'].mean():+.2f}% (n={len(post)}) ==")
print(f"cap drag: pre={pre['cap_loss_pct'].mean():.3f}%  post={post['cap_loss_pct'].mean():.3f}%")
# buy&hold total context
bh=100*(c['spot_exp'].iloc[-1]-c['spot_ent'].iloc[0])/c['spot_ent'].iloc[0]
print(f"\nNIFTY buy&hold over window (spot): {bh:+.0f}%  ({c['spot_ent'].iloc[0]:.0f} -> {c['spot_exp'].iloc[-1]:.0f})")
c.to_csv(f"{SC}/cycles_analyzed.csv",index=False)
