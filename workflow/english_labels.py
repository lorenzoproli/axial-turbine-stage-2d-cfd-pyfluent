"""English presentation labels; native Fluent identifiers remain traceable."""
TRANSLATIONS = {'forza_y_rotore': 'Rotor tangential force', 'mdot_inlet': 'Inlet mass flow', 'mdot_outlet': 'Outlet mass flow', 'pt_outlet': 'Outlet total pressure', 'wall_statore': 'Stator blade', 'wall_rotore': 'Rotor blade', 'baseline_adattata': 'Historical adapted mesh', '_setup_verificato': ' (verified setup)', 'ciclo ': 'cycle ', ' campioni': ' samples', 'Qualità ortogonale': 'Orthogonal quality', 'Statore': 'Stator', 'Rotore': 'Rotor', 'statore': 'stator', 'rotore': 'rotor', 'profondità': 'depth', 'profonditÃ\xa0': 'depth', 'Percentuale delle celle nella classe': 'Cells in bin', 'distribuzioni native Fluent, pesatura per numero di celle': 'Native Fluent distributions, weighted by cell count', 'X assiale': 'Axial X', 'Y tangenziale': 'Tangential Y', 'localizzazione delle celle con qualità ortogonale': 'Locations of cells with orthogonal quality', 'Nessuna cella con Q<0.1': 'No cells with Q<0.1', 'Dominio completo: un passaggio per schiera': 'Full domain: one passage per row', 'Bordo di attacco e strati vicino alla parete': 'Leading edge and near-wall layers', 'Interfaccia sliding: lati statore e rotore': 'Sliding interface: stator and rotor sides', 'Lati reali delle celle; nessuna triangolazione aggiunta': 'Actual cell edges; no added triangulation', 'Geometria di riferimento; nessuna soluzione CFD': 'Reference geometry; no CFD solution', 'mesh sistematica dalla geometria comune': 'systematic mesh from the common geometry', 'Baseline storica: mesh adattata mantenuta fissa': 'Historical baseline: fixed adapted mesh', 'Mesh sistematiche: dettaglio degli strati al bordo di attacco': 'Systematic meshes: leading-edge layer detail', 'Mesh adattata fissa: finestre equivalenti di tre periodi dopo assestamento': 'Fixed adapted mesh: equivalent three-period windows after settling', 'Famiglia sistematica: stesso dt, fase e finestra statistica': 'Systematic family: common timestep and phase, three-period windows', 'Tempo fisico': 'Physical time', 'Tempo / T (riferimento)': 'Time / T (reference)', 'Fase rispetto all’inizio della finestra': 'Phase from window start', 'Fase relativa della finestra': 'Phase from window start', 'Fase relativa t/T mod 1': 'Phase t/T mod 1', 'tre periodi completi dopo l’assestamento escluso': 'three complete periods after excluded settling', 'tre periodi completi dopo l assestamento escluso': 'three complete periods after excluded settling', 'Ciclo': 'Cycle', 'Media temporale': 'Time mean', 'Media': 'Mean', 'Ampiezza picco-picco': 'Peak-to-peak amplitude', 'Pressione statica assoluta': 'Absolute static pressure', 'Mach assoluto': 'Absolute Mach number', 'Inviluppo campionato': 'Sampled envelope', 'Pareti alla stessa fase': 'Blade surfaces at a common phase', 'Residuo scalato a fine passo': 'Scaled residual at step end', 'residui finali; non costituiscono da soli un criterio di convergenza': 'end-of-step residuals; additional convergence checks required', 'Armonica della frequenza di passaggio': 'Blade-passing harmonic', 'Ampiezza di picco': 'Peak amplitude', 'Componenti periodiche su tre cicli': 'Periodic components over three cycles', 'fase riferita all inizio della finestra': 'phase referenced to window start', 'Celle attive': 'Active cells', 'Monitor storici: finestra finale di tre periodi completi': 'Historical monitors: final three complete periods', 'Confronto in fase: tre cicli completi, nessun tratto pre-AMR incluso': 'Phase comparison: three complete cycles after mesh adaptation', 'unità da confermare': 'native monitor units'}

def translate(value):
    value = str(value)
    for old, new in sorted(TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
        value = value.replace(old, new)
    return value

def install():
    from matplotlib.figure import Figure
    from matplotlib.text import Text
    if getattr(Figure.savefig, 'english_labels_installed', False):
        return
    original = Figure.savefig

    def savefig(figure, *args, **kwargs):
        for artist in figure.findobj(match=Text):
            artist.set_text(translate(artist.get_text()))
        return original(figure, *args, **kwargs)
    savefig.english_labels_installed = True
    Figure.savefig = savefig
