"use client";
import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import Navbar from "@/components/Navbar";
import ProtectedRoute from "@/components/ProtectedRoute";

const OWM_KEY = process.env.NEXT_PUBLIC_OPENWEATHER_KEY || "";

/* ── Layer definitions ── */
const LAYERS = [
    { id: "precipitation_new", owm: "precipitation_new", label: "🌧️ Rainfall", color: "#4FC3F7", particle: "#60DFFF", desc: "Live precipitation intensity (mm/hr)" },
    { id: "wind_new", owm: "wind_new", label: "💨 Wind", color: "#80DEEA", particle: "#B2EBF2", desc: "Surface wind speed & direction (m/s)" },
    { id: "clouds_new", owm: "clouds_new", label: "☁️ Clouds", color: "#90A4AE", particle: "#CFD8DC", desc: "Total cloud cover (%)" },
    { id: "temp_new", owm: "temp_new", label: "🌡️ Temperature", color: "#FF8A65", particle: "#FFAB76", desc: "Surface temperature (°C)" },
    { id: "pressure_new", owm: "pressure_new", label: "🧭 Pressure", color: "#CE93D8", particle: "#E1BEE7", desc: "Atmospheric pressure (hPa)" },
];

const INDIA = { lat: 21.0, lon: 78.0, zoom: 5 };

const REGIONS = [
    { label: "All India", lat: 21.0, lon: 78.0, zoom: 5 },
    { label: "North India", lat: 28.6, lon: 77.2, zoom: 6 },
    { label: "Maharashtra", lat: 19.7, lon: 75.7, zoom: 6 },
    { label: "Punjab", lat: 31.1, lon: 75.3, zoom: 7 },
    { label: "Karnataka", lat: 15.3, lon: 75.7, zoom: 6 },
    { label: "Andhra", lat: 15.9, lon: 79.7, zoom: 6 },
    { label: "Tamil Nadu", lat: 11.1, lon: 78.6, zoom: 6 },
    { label: "Gujarat", lat: 22.3, lon: 71.2, zoom: 6 },
];

export default function ClimateMapPage() {
    const [activeLayer, setActiveLayer] = useState(LAYERS[1]); // Default to Wind
    const [coords, setCoords] = useState(INDIA);
    const [mounted, setMounted] = useState(false);
    const mapIframeRef = useRef<HTMLIFrameElement>(null);
    const [riskData, setRiskData] = useState<any>(null);
    const [loadingRisk, setLoadingRisk] = useState(false);
    const [imdAlert, setImdAlert] = useState<string>("");

    useEffect(() => { setMounted(true); }, []);

    /* ── Sync Map via postMessage to avoid reload jitter ── */
    useEffect(() => {
        if (!mounted || !mapIframeRef.current) return;
        const msg = { type: 'SYNC_MAP', lat: coords.lat, lon: coords.lon, zoom: coords.zoom, layer: activeLayer.owm, key: OWM_KEY, color: activeLayer.color };
        mapIframeRef.current.contentWindow?.postMessage(msg, "*");
    }, [coords, activeLayer, mounted]);

    /* ── Fetch Crop Risk Intelligence ── */
    useEffect(() => {
        if (!mounted) return;
        const fetchRisk = async () => {
            setLoadingRisk(true);
            try {
                const res = await fetch("/api/crop-risk", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ lat: coords.lat, lon: coords.lon, crop: "Paddy", stage: "Vegetative", lang: "en" })
                });
                if (res.ok) setRiskData(await res.json());
            } catch (e) {
                console.error("Risk fetch failed", e);
            }
            setLoadingRisk(false);
        };
        fetchRisk();
    }, [coords, mounted]);

    /* ── IMD Rotating Alerts ── */
    useEffect(() => {
        const ALERTS = [
            "⚡ IMD WARNING: Thunderstorm likely over Punjab, Haryana (next 24h)",
            "🌊 CYCLONE WATCH: Bay of Bengal system tracking towards Odisha coast",
            "🌡️ HEAT WAVE: Severe heat conditions over Vidarbha",
            "🌧️ HEAVY RAINFALL ALERT: Karnataka, Kerala — Red Alert issued",
        ];
        let idx = 0;
        setImdAlert(ALERTS[0]);
        const t = setInterval(() => { idx = (idx + 1) % ALERTS.length; setImdAlert(ALERTS[idx]); }, 5000);
        return () => clearInterval(t);
    }, []);

    const mapHtml = useMemo(() => `<!DOCTYPE html><html><head>
    <meta charset="utf-8"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <style>
        html,body,#map{height:100%;margin:0;padding:0;background:#030708;overflow:hidden;}
        .leaflet-container{background:#030708!important;}
        .leaflet-tile-pane{filter:saturate(1.2) brightness(0.7) contrast(1.1);}
        canvas{pointer-events:none;z-index:1000;position:absolute;top:0;left:0;}
    </style></head><body>
    <div id="map"></div>
    <canvas id="particles"></canvas>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map=L.map('map',{zoomControl:false,attributionControl:false}).setView([${coords.lat},${coords.lon}],${coords.zoom});
        var base=L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png').addTo(map);
        var weatherLayer=null;
        var currentPartColor='${activeLayer.particle}';
    
        function updateLayer(l, k){
            if(weatherLayer) map.removeLayer(weatherLayer);
            if(l && k) {
                weatherLayer = L.tileLayer('https://tile.openweathermap.org/map/'+l+'/{z}/{x}/{y}.png?appid='+k, {opacity:0.65});
                weatherLayer.addTo(map);
            }
        }
        updateLayer('${activeLayer.owm}', '${OWM_KEY}');
    
        // Particle Flow Simulation
        const canvas=document.getElementById('particles');
        const ctx=canvas.getContext('2d');
        let particles=[];
    
        function resize(){ canvas.width=window.innerWidth; canvas.height=window.innerHeight; }
        window.addEventListener('resize', resize); resize();
    
        class Particle {
            constructor(){ this.init(); }
            init(){
                this.x=Math.random()*canvas.width; this.y=Math.random()*canvas.height;
                this.vx=(Math.random()-0.5)*2 + 2; this.vy=(Math.random()-0.5)*0.5;
                this.life=Math.random()*100+50; this.alpha=Math.random()*0.5;
            }
            update(){
                this.x+=this.vx; this.y+=this.vy; this.life--;
                if(this.x>canvas.width || this.x<0 || this.y>canvas.height || this.y<0 || this.life<0) this.init();
            }
            draw(){
                ctx.beginPath(); ctx.strokeStyle=currentPartColor; ctx.globalAlpha=this.alpha*(this.life/100);
                ctx.lineWidth=1; ctx.moveTo(this.x,this.y); ctx.lineTo(this.x-this.vx*2,this.y-this.vy*2); ctx.stroke();
            }
        }
        for(let i=0;i<150;i++) particles.push(new Particle());
        function anim(){
            ctx.clearRect(0,0,canvas.width,canvas.height);
            particles.forEach(p=>{p.update(); p.draw();}); requestAnimationFrame(anim);
        }
        anim();
    
        window.onmessage=function(e){
            var d=e.data;
            if(d.type==='SYNC_MAP'){
                map.flyTo([d.lat,d.lon], d.zoom, {animate:true, duration:1.5});
                updateLayer(d.layer, d.key);
                currentPartColor=d.color;
            }
        }
    </script></body></html>`, []);

    if (!mounted) return null;

    return (
        <ProtectedRoute>
            <div style={{ minHeight: "100vh", background: "#030708", color: "#E8F5E9", fontFamily: "var(--font-body)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
                <Navbar />

                {/* 🚨 Ticker Banner with IMD Alerts */}
                <div style={{
                    marginTop: "64px", height: "32px", background: "rgba(255,160,0,0.1)",
                    borderBottom: "1px solid rgba(255,160,0,0.2)", display: "flex", alignItems: "center",
                    overflow: "hidden", position: "relative", zIndex: 10
                }}>
                    <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "120px", background: "#FF8F00", color: "#000", fontSize: "0.65rem", fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center", letterSpacing: "1px", zIndex: 2 }}>
                        LIVE ALERTS
                    </div>
                    <div style={{ flex: 1, paddingLeft: "135px", color: "#FFCA28", fontSize: "0.75rem", fontFamily: "var(--font-mono)", whiteSpace: "nowrap", animation: "ticker 20s linear infinite" }}>
                        {Array(5).fill(imdAlert).join(" ⚡ ")}
                    </div>
                </div>

                <div style={{ flex: 1, display: "grid", gridTemplateColumns: "380px 1fr", position: "relative" }}>

                    {/* 🎮 Map Controls Glass Sidebar */}
                    <div style={{
                        background: "rgba(3,7,8,0.85)", backdropFilter: "blur(20px)",
                        borderRight: "1px solid rgba(255,255,255,0.05)", padding: "1.5rem",
                        display: "flex", flexDirection: "column", gap: "1.5rem", zIndex: 10,
                        boxShadow: "20px 0 50px rgba(0,0,0,0.5)"
                    }}>
                        <div>
                            <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "#ADFF2F", marginBottom: "0.5rem", letterSpacing: "-0.5px" }}>CLIMATE INTELLIGENCE</h2>
                            <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", lineHeight: 1.5 }}>AI-powered multi-layer weather telemetry for precision farming.</p>
                        </div>

                        {/* Location Selector */}
                        <div>
                            <label style={{ fontSize: "0.65rem", fontWeight: 700, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", marginBottom: "0.5rem", display: "block" }}>REGION MONITORING</label>
                            <div style={{ position: "relative" }}>
                                <select
                                    style={{ width: "100%", padding: "0.85rem", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", borderRadius: "12px", outline: "none", appearance: "none", fontSize: "0.9rem" }}
                                    onChange={(e) => {
                                        const r = REGIONS.find(x => x.label === e.target.value);
                                        if (r) setCoords(r);
                                    }}
                                >
                                    {REGIONS.map(r => <option key={r.label} value={r.label} style={{ background: "#030708" }}>{r.label}</option>)}
                                </select>
                            </div>
                        </div>

                        {/* Layer Switcher */}
                        <div>
                            <label style={{ fontSize: "0.65rem", fontWeight: 700, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", marginBottom: "0.8rem", display: "block" }}>SATELLITE TELEMETRY</label>
                            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                                {LAYERS.map(L => (
                                    <button
                                        key={L.id}
                                        onClick={() => setActiveLayer(L)}
                                        style={{
                                            padding: "1rem", borderRadius: "14px", border: activeLayer.id === L.id ? `1px solid ${L.color}` : "1px solid rgba(255,255,255,0.05)",
                                            background: activeLayer.id === L.id ? `${L.color}15` : "rgba(255,255,255,0.02)",
                                            color: activeLayer.id === L.id ? "#fff" : "rgba(255,255,255,0.5)",
                                            display: "flex", alignItems: "center", gap: "12px", cursor: "pointer", transition: "all 0.3s ease", textAlign: "left"
                                        }}
                                    >
                                        <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: activeLayer.id === L.id ? L.color : "rgba(255,255,255,0.1)", boxShadow: activeLayer.id === L.id ? `0 0 10px ${L.color}` : "none" }} />
                                        <div>
                                            <div style={{ fontSize: "0.85rem", fontWeight: 700 }}>{L.label}</div>
                                            <div style={{ fontSize: "0.6rem", opacity: 0.6, marginTop: "2px" }}>{L.desc}</div>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Current Risk Card */}
                        {riskData && (
                            <div style={{
                                marginTop: "auto", background: "rgba(173,255,47,0.05)", border: "1px solid rgba(173,255,47,0.15)",
                                borderRadius: "16px", padding: "1.25rem", display: "flex", flexDirection: "column", gap: "10px"
                            }}>
                                <div style={{ fontSize: "0.6rem", fontWeight: 800, color: "#ADFF2F", textTransform: "uppercase" }}>AI Risk Index</div>
                                <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
                                    <span style={{ fontSize: "2rem", fontWeight: 900, color: riskData.risk.color === "🔴" ? "#FF3B3B" : "#ADFF2F" }}>{riskData.risk.score}%</span>
                                    <span style={{ fontSize: "0.8rem", fontWeight: 700, opacity: 0.8 }}>{riskData.risk.level}</span>
                                </div>
                                <div style={{ fontSize: "0.75rem", lineHeight: 1.5, opacity: 0.7 }}>
                                    Current forecast suggests {riskData.risk.level.toLowerCase()} pressure on {riskData.crop}.
                                </div>
                            </div>
                        )}
                    </div>

                    {/* 📍 Main Map Screen */}
                    <main style={{ position: "relative", overflow: "hidden" }}>
                        <iframe
                            ref={mapIframeRef}
                            srcDoc={mapHtml}
                            style={{ width: "100%", height: "100%", border: "none" }}
                            title="weather-map"
                        />

                        {/* AI Analysis Floating Card */}
                        {riskData && (
                            <div style={{
                                position: "absolute", bottom: "30px", right: "30px", width: "420px",
                                background: "rgba(5, 10, 15, 0.7)", backdropFilter: "blur(30px) saturate(160%)",
                                border: "1px solid rgba(255,255,255,0.08)", borderRadius: "24px",
                                padding: "1.75rem", boxShadow: "0 30px 60px rgba(0,0,0,0.6)", zIndex: 20,
                                display: "flex", flexDirection: "column", gap: "1rem"
                            }}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                                    <div>
                                        <div style={{ color: "#ADFF2F", fontSize: "0.65rem", fontWeight: 900, letterSpacing: "1px" }}>FIELD TELEMETRY</div>
                                        <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 800 }}>🌾 {riskData.crop} Analysis</h3>
                                    </div>
                                    <div style={{ background: "rgba(255,255,255,0.05)", padding: "10px", borderRadius: "15px", textAlign: "center", minWidth: "60px" }}>
                                        <div style={{ fontSize: "1.5rem", fontWeight: 900, color: "#ADFF2F" }}>{riskData.risk.score}%</div>
                                        <div style={{ fontSize: "0.5rem", opacity: 0.5 }}>SCORE</div>
                                    </div>
                                </div>

                                <div style={{ fontSize: "0.85rem", lineHeight: 1.7, color: "rgba(255,255,255,0.85)", fontStyle: "italic", background: "rgba(255,255,255,0.03)", padding: "15px", borderRadius: "15px", borderLeft: "4px solid #ADFF2F" }}>
                                    {riskData.explanation || riskData.ai_advice}
                                </div>

                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "1rem" }}>
                                    <span style={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.4)" }}>Updated: {riskData.timestamp}</span>
                                    <div style={{ display: "flex", gap: "8px" }}>
                                        {riskData.risk.threats_detected?.slice(0, 2).map((t: string, i: number) => (
                                            <span key={i} style={{ background: "rgba(255,0,0,0.15)", color: "#FF3B3B", fontSize: "0.65rem", padding: "4px 8px", borderRadius: "6px", fontWeight: 700 }}>{t.split('(')[0].trim()}</span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}
                    </main>
                </div>

                <style>{`
                    @keyframes ticker {
                        0% { transform: translateX(0); }
                        100% { transform: translateX(-50%); }
                    }
                `}</style>
            </div>
        </ProtectedRoute>
    );
}
