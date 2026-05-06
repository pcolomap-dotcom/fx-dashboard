"""
  Dashboard FX: CLP/EUR, USD/EUR, CLP/USD                                                                                                         ---------------------------------------
  - Descarga 30 días de tipos de cambio. Fuente principal: mindicador.cl (Banco
    Central de Chile, gratis, sin key). Fallback: api.frankfurter.app (BCE).
  - Calcula estadísticas, tendencia (regresión lineal últimos 7 días) y bandas ±1σ
    como margen sugerido de compra/venta sobre la media de 30 días.
  - Genera `dashboard.html` autocontenido (Plotly desde CDN) y lo abre en el navegador.

  Uso:
      python fx_dashboard.py [--dias 30] [--no-abrir]
  """
  from __future__ import annotations

  import argparse
  import json
  import statistics
  import urllib.request
  import urllib.error
  import webbrowser
  from datetime import date, datetime, timedelta
  from pathlib import Path

  FRANKFURTER_URL = "https://api.frankfurter.app/{start}..{end}?from=EUR&to=CLP,USD"
  MINDICADOR_URL = "https://mindicador.cl/api/{indicador}/{year}"

  UA = "Mozilla/5.0 (compatible; fx-dashboard/1.0; +https://github.com/)"


  # ----------------------------- Datos -----------------------------------------

  def _http_json(url: str, timeout: int = 20) -> dict:
      req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
      with urllib.request.urlopen(req, timeout=timeout) as r:
          return json.loads(r.read())


  def _serie_to_map(serie: list[dict]) -> dict[str, float]:
      """[{fecha:'YYYY-MM-DDTHH:MM:SSZ', valor: 950.5}, …]  →  {'YYYY-MM-DD': 950.5}"""
      return {item["fecha"][:10]: float(item["valor"]) for item in serie}


  def fetch_from_mindicador(dias: int) -> dict:
      """
      Fuente: mindicador.cl (Banco Central de Chile). Devuelve el dict normalizado al
      mismo formato que Frankfurter: {"rates": {"YYYY-MM-DD": {"CLP": …, "USD": …}}}
      donde CLP y USD son las unidades por 1 EUR.
      """
      today = date.today()
      # mindicador.cl indexa por año; cubrimos el actual y, si la ventana cruza,
      # también el anterior (caso típico al ejecutarse en enero).
      years = {today.year}
      if (today - timedelta(days=dias + 7)).year != today.year:
          years.add(today.year - 1)

      clp_per_eur: dict[str, float] = {}
      clp_per_usd: dict[str, float] = {}
      for y in sorted(years):
          eur = _http_json(MINDICADOR_URL.format(indicador="euro",  year=y))
          usd = _http_json(MINDICADOR_URL.format(indicador="dolar", year=y))
          clp_per_eur.update(_serie_to_map(eur["serie"]))
          clp_per_usd.update(_serie_to_map(usd["serie"]))

      # Solo fechas presentes en ambas series; USD/EUR se deriva como CLP/EUR ÷ CLP/USD.
      rates = {}
      for fecha, clp_eur in clp_per_eur.items():
          clp_usd = clp_per_usd.get(fecha)
          if clp_usd:
              rates[fecha] = {"CLP": clp_eur, "USD": clp_eur / clp_usd}
      if not rates:
          raise RuntimeError("mindicador.cl no devolvió fechas comunes EUR/USD")
      return {"rates": rates}


  def fetch_from_frankfurter(dias: int) -> dict:
      """Fallback: api.frankfurter.app (BCE). Suele bloquearse desde IPs de GH Actions."""
      end = date.today()
      start = end - timedelta(days=dias + 7)
      return _http_json(FRANKFURTER_URL.format(start=start.isoformat(), end=end.isoformat()))


  def fetch_history(dias: int) -> dict:
      """Intenta varias fuentes en cascada. Lanza SystemExit con el detalle si fallan todas."""
      fuentes = (
          ("mindicador.cl (BCCh)",   lambda: fetch_from_mindicador(dias)),
          ("frankfurter.app (BCE)",  lambda: fetch_from_frankfurter(dias)),
      )
      errores = []
      for nombre, fn in fuentes:
          try:
              print(f"  · Probando {nombre}…")
              raw = fn()
              if raw.get("rates"):
                  print(f"  ✓ Datos obtenidos de {nombre} ({len(raw['rates'])} días)")
                  return raw
              errores.append(f"{nombre}: respuesta sin tasas")
          except (urllib.error.HTTPError, urllib.error.URLError,
                  KeyError, ValueError, RuntimeError, TimeoutError) as e:
              errores.append(f"{nombre}: {type(e).__name__}: {e}")
      raise SystemExit("No se pudo obtener datos de ninguna fuente:\n  - " + "\n  - ".join(errores))


  def build_series(raw: dict, dias: int) -> dict:
      """Series ordenadas por fecha para los 3 pares (últimos `dias` de cotización disponibles)."""
      items = sorted(raw["rates"].items())[-dias:]
      fechas = [d for d, _ in items]
      clp_eur = [v["CLP"] for _, v in items]               # CLP por 1 EUR
      usd_eur = [v["USD"] for _, v in items]               # USD por 1 EUR
      clp_usd = [c / u for c, u in zip(clp_eur, usd_eur)]  # CLP por 1 USD (cruz)
      return {"fechas": fechas, "CLP/EUR": clp_eur, "USD/EUR": usd_eur, "CLP/USD": clp_usd}


  # ----------------------------- Análisis --------------------------------------

  def stats(values: list[float]) -> dict:
      """Estadísticas: media, σ, bandas, variación 30d y pendiente últimos 7 puntos."""
      n = len(values)
      media = statistics.fmean(values)
      sd = statistics.pstdev(values) if n > 1 else 0.0

      # Pendiente por mínimos cuadrados sobre los últimos 7 puntos -> %/día
      recent = values[-min(7, n):]
      xs = list(range(len(recent)))
      if len(recent) > 1:
          mx, my = statistics.fmean(xs), statistics.fmean(recent)
          num = sum((x - mx) * (y - my) for x, y in zip(xs, recent))
          den = sum((x - mx) ** 2 for x in xs)
          slope = num / den if den else 0.0
      else:
          slope = 0.0

      actual = values[-1]
      return {
          "actual":         actual,
          "min":            min(values),
          "max":            max(values),
          "media":          media,
          "desv":           sd,
          "banda_baja":     media - sd,    # margen de COMPRA
          "banda_alta":     media + sd,    # margen de VENTA
          "var_pct_30d":    (actual / values[0] - 1) * 100 if values[0] else 0.0,
          "tendencia_dia":  (slope / media * 100) if media else 0.0,  # %/día
      }


  def recommend(s: dict, par: str) -> tuple[str, str, str]:
      """
      Señal pensada como: COMPRAR la divisa cotizada (a la derecha del par) usando la base.
      Ej: 'COMPRAR' en CLP/USD => buen momento para comprar USD pagando con CLP.
      """
      actual, baja, alta, media = s["actual"], s["banda_baja"], s["banda_alta"], s["media"]
      base, quote = par.split("/")
      accion = f"comprar {quote} con {base}"

      if actual <= baja:
          return ("COMPRAR FUERTE", "#1b5e20",
                  f"{actual:,.4f} ≤ banda inferior ({baja:,.4f}). Históricamente barato → "
                  f"momento favorable para {accion}.")
      if actual < media:
          return ("COMPRAR", "#43a047",
                  f"{actual:,.4f} bajo la media 30d ({media:,.4f}). Inclinación a {accion}.")
      if actual >= alta:
          return ("VENDER FUERTE", "#b71c1c",
                  f"{actual:,.4f} ≥ banda superior ({alta:,.4f}). Históricamente caro → "
                  f"momento favorable para vender {quote} y comprar {base}.")
      if actual > media:
          return ("VENDER", "#e53935",
                  f"{actual:,.4f} sobre la media 30d ({media:,.4f}). Inclinación a vender {quote}.")
      return ("MANTENER", "#616161", f"{actual:,.4f} en línea con la media. Sin sesgo claro.")


  # ----------------------------- HTML ------------------------------------------

  CSS = """
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, Segoe UI, Roboto, sans-serif;
         background: #0f1419; color: #e6edf3; }
  header { padding: 24px 32px; border-bottom: 1px solid #21262d; }
  header h1 { margin: 0 0 4px; font-size: 22px; }
  header .sub { color: #8b949e; font-size: 13px; }
  main { padding: 24px 32px; max-width: 1400px; margin: 0 auto; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
           gap: 16px; margin-bottom: 24px; }
  .card { background: #161b22; border: 1px solid #21262d; border-radius: 10px; padding: 20px; }
  .card h2 { margin: 0 0 12px; font-size: 16px; color: #8b949e; font-weight: 500; }
  .price { font-size: 30px; font-weight: 600; }
  .var { font-size: 13px; margin-top: 4px; }
  .var.up { color: #56d364; } .var.down { color: #f85149; }
  .signal { display: inline-block; margin-top: 14px; padding: 6px 14px;
            border-radius: 999px; color: white; font-size: 13px; font-weight: 600; }
  .expl { margin-top: 10px; font-size: 13px; color: #8b949e; line-height: 1.5; }
  .grid-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px;
                margin-top: 14px; font-size: 12px; }
  .grid-stats span { color: #8b949e; }
  .chart { background: #161b22; border: 1px solid #21262d; border-radius: 10px;
           padding: 12px; margin-bottom: 16px; }
  footer { padding: 20px 32px; color: #8b949e; font-size: 12px; border-top: 1px solid #21262d; }
  .legend-help { background:#161b22; border:1px solid #21262d; border-radius:10px;
                 padding:16px 20px; margin-top:8px; font-size:13px; color:#c9d1d9; line-height:1.6;}
  """

  PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


  def fmt(x: float, dec: int = 4) -> str:
      return f"{x:,.{dec}f}"


  def card_html(par: str, s: dict, signal: tuple) -> str:
      senal, color, expl = signal
      var = s["var_pct_30d"]
      var_class = "up" if var >= 0 else "down"
      var_sign = "▲" if var >= 0 else "▼"
      tend = s["tendencia_dia"]
      tend_sign = "▲" if tend >= 0 else "▼"
      return f"""
      <div class="card">
        <h2>{par}</h2>
        <div class="price">{fmt(s['actual'])}</div>
        <div class="var {var_class}">{var_sign} {var:+.2f}% en 30 días &nbsp;·&nbsp; {tend_sign} {tend:+.3f}%/día (tendencia 7d)</div>
        <span class="signal" style="background:{color}">{senal}</span>
        <div class="expl">{expl}</div>
        <div class="grid-stats">
          <span>Mín 30d</span><b>{fmt(s['min'])}</b>
          <span>Máx 30d</span><b>{fmt(s['max'])}</b>
          <span>Media 30d</span><b>{fmt(s['media'])}</b>
          <span>Desv. (σ)</span><b>{fmt(s['desv'])}</b>
          <span>Margen compra (μ−σ)</span><b style="color:#56d364">{fmt(s['banda_baja'])}</b>
          <span>Margen venta (μ+σ)</span><b style="color:#f85149">{fmt(s['banda_alta'])}</b>
        </div>
      </div>
      """


  def render_html(series: dict, all_stats: dict, recs: dict) -> str:
      cards = "\n".join(card_html(p, all_stats[p], recs[p]) for p in ("CLP/EUR", "USD/EUR", "CLP/USD"))
      payload = json.dumps({"fechas": series["fechas"],
                            "pares": {p: series[p] for p in ("CLP/EUR", "USD/EUR", "CLP/USD")},
                            "stats": all_stats}, ensure_ascii=False)

      js = """
      const D = __DATA__;
      const layout_base = (title) => ({
          title: { text: title, font: {color:'#e6edf3', size:14} },
          paper_bgcolor: '#161b22', plot_bgcolor: '#161b22',
          font: { color: '#c9d1d9' },
          margin: { l: 60, r: 20, t: 40, b: 40 },
          xaxis: { gridcolor: '#21262d' },
          yaxis: { gridcolor: '#21262d' },
          hovermode: 'x unified',
          showlegend: true,
          legend: { orientation: 'h', y: -0.18 }
      });
      Object.entries(D.pares).forEach(([par, valores], i) => {
          const st = D.stats[par];
          const traces = [
              { x: D.fechas, y: valores, name: par, type:'scatter', mode:'lines',
                line:{color:'#58a6ff', width:2.5} },
              { x: D.fechas, y: D.fechas.map(()=>st.media), name:'Media 30d',
                type:'scatter', mode:'lines', line:{color:'#8b949e', dash:'dash', width:1.5}},
              { x: D.fechas, y: D.fechas.map(()=>st.banda_alta), name:'Margen venta (μ+σ)',
                type:'scatter', mode:'lines', line:{color:'#f85149', dash:'dot', width:1}},
              { x: D.fechas, y: D.fechas.map(()=>st.banda_baja), name:'Margen compra (μ−σ)',
                type:'scatter', mode:'lines', line:{color:'#56d364', dash:'dot', width:1},
                fill:'tonexty', fillcolor:'rgba(139,148,158,0.08)'}
          ];
          Plotly.newPlot('chart-'+i, traces, layout_base(par), {displayModeBar:false, responsive:true});
      });
      """.replace("__DATA__", payload)

      return f"""<!doctype html>
  <html lang="es"><head><meta charset="utf-8">
  <title>Dashboard FX · CLP/EUR · USD/EUR · CLP/USD</title>
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#0f1419">
  <meta name="description" content="Dashboard de tipos de cambio CLP/EUR, USD/EUR, CLP/USD con tendencias y márgenes.">
  <!-- PWA / instalable en iPhone (Compartir → Añadir a pantalla de inicio) -->
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="FX">
  <link rel="apple-touch-icon" href="icon.svg">
  <link rel="icon" type="image/svg+xml" href="icon.svg">
  <script src="{PLOTLY_CDN}"></script>
  <style>{CSS}</style></head><body>
  <header>
    <h1>Dashboard FX — Tendencias y márgenes a 30 días</h1>
    <div class="sub">Datos: mindicador.cl (Banco Central de Chile) · Generado: {datetime.now():%Y-%m-%d %H:%M}</div>
  </header>
  <main>
    <div class="cards">{cards}</div>
    <div class="chart"><div id="chart-0" style="height:340px"></div></div>
    <div class="chart"><div id="chart-1" style="height:340px"></div></div>
    <div class="chart"><div id="chart-2" style="height:340px"></div></div>
    <div class="legend-help">
      <b>Cómo leer las señales</b><br>
      Las bandas <span style="color:#56d364">verde</span> y
      <span style="color:#f85149">roja</span> son <code>media ± 1σ</code> de los últimos 30 días.
      Cuando el precio toca o cruza una banda hay ~68% de probabilidad histórica de que vuelva
      hacia la media (<i>mean reversion</i>) — ahí están los <b>márgenes recomendados</b>.<br>
      “COMPRAR” en <code>CLP/USD</code> = el USD está barato en pesos → buen momento de pasar CLP→USD.<br>
      “VENDER” en <code>CLP/USD</code> = el USD está caro en pesos → buen momento de pasar USD→CLP.<br>
      <b>Aviso:</b> análisis técnico básico, no constituye asesoría financiera.
    </div>
  </main>
  <footer>Tipos de cambio publicados por el Banco Central de Chile (días hábiles, sin festivos ni fines de semana).</footer>
  <script>{js}</script>
  </body></html>
  """


  # ----------------------------- Main ------------------------------------------

  def main() -> None:
      parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
      parser.add_argument("--dias", type=int, default=30, help="Ventana histórica (por defecto 30)")
      parser.add_argument("--no-abrir", action="store_true", help="No abrir el navegador al terminar")
      parser.add_argument("--salida", default="dashboard.html", help="Archivo HTML de salida")
      args = parser.parse_args()

      print(f"→ Descargando histórico de {args.dias} días…")
      raw = fetch_history(args.dias)
      series = build_series(raw, args.dias)
      pares = ("CLP/EUR", "USD/EUR", "CLP/USD")
      all_stats = {p: stats(series[p]) for p in pares}
      recs = {p: recommend(all_stats[p], p) for p in pares}

      # Resumen por consola
      print(f"\nVentana: {series['fechas'][0]} → {series['fechas'][-1]}  ({len(series['fechas'])} días hábiles)\n")
      for p in pares:
          s, (sig, _, _) = all_stats[p], recs[p]
          print(f"  {p:8}  actual={s['actual']:>12,.4f}   media={s['media']:>12,.4f}   "
                f"σ={s['desv']:>9,.4f}   30d={s['var_pct_30d']:+6.2f}%   →  {sig}")

      out = Path(args.salida).resolve()
      out.write_text(render_html(series, all_stats, recs), encoding="utf-8")
      print(f"\n✓ Dashboard generado: {out}")

      if not args.no_abrir:
          webbrowser.open(out.as_uri())


  if __name__ == "__main__":
      main()
