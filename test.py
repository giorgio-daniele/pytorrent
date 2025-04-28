


tot_size = pow(2, 10) + 1
pcs_size = pow(2, 3)
blk_size = pow(2, 2)

blks = []
off  = 0
while off < tot_size:
    # Calcolo la dimensione effettiva del pezzo (potrebbe essere più piccolo all'ultimo giro)
    curr_pcs_size = min(pcs_size, tot_size - off)
    
    # Ora divido il pezzo in blocchi
    pcs_off = off
    while pcs_off < off + curr_pcs_size:
        curr_blk_size = min(blk_size, off + curr_pcs_size - pcs_off)
        blks.append((pcs_off, pcs_off + curr_blk_size - 1))
        pcs_off += curr_blk_size
    off += curr_pcs_size

# Stampiamo il risultato
for i, (start, end) in enumerate(blks):
    print(f"Blocco {i}: da {start} a {end} (size={end-start+1})")