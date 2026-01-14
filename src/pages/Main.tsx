import React from 'react';
import { Terminal, Shield, Zap, Activity, Globe, Database } from 'lucide-react';

const MainDashboard: React.FC = () => {
  return (
    <div className="min-h-screen bg-black text-green-500 p-4 md:p-8 font-mono relative">
      {/* Header HUD */}
      <header className="border-b border-green-900 pb-4 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl md:text-4xl font-bold tracking-tighter flex items-center gap-2">
            <Shield className="text-red-600 animate-pulse" size={32} />
            DEADMAN // INTEL COMMAND
          </h1>
          <p className="text-xs md:text-sm text-green-800 uppercase tracking-widest">NASA-Standard Autopilot Active</p>
        </div>
        <div className="flex gap-4 text-xs">
          <div className="border border-green-900 p-2 rounded bg-green-900/10">
            SYS_STATUS: <span className="text-green-400">NOMINAL</span>
          </div>
          <div className="border border-green-900 p-2 rounded bg-green-900/10">
            TOR_CIRCUIT: <span className="text-cyan-400">ENCRYPTED</span>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Telemetry Block */}
        <section className="md:col-span-2 border border-green-900 bg-green-900/5 rounded-lg p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-2 text-green-900"><Activity size={48} /></div>
          <h2 className="text-xl mb-4 flex items-center gap-2 underline underline-offset-8">MISSION_LOGS</h2>
          <div className="space-y-2 text-sm md:text-base">
            <p className="text-green-400">[04:51:22] Initializing Absolute Freedom protocols...</p>
            <p className="text-white">[04:51:39] TOR Circuit Established: Exit IP 185.220.101.42</p>
            <p className="text-green-400">[04:52:08] Bypassing Reddit 403 via Layer 4 Proxy...</p>
            <p className="text-red-500">[04:53:48] ALERT: SynthID Bypass Weaponry Detected</p>
            <p className="text-cyan-400 cursor-blink">_</p>
          </div>
        </section>

        {/* Quick Actions */}
        <section className="space-y-6">
          <div className="border border-green-900 bg-black p-4 rounded hover:bg-green-900/20 transition-all cursor-pointer group">
            <div className="flex items-center gap-3">
              <Zap className="group-hover:text-white" />
              <div>
                <h3 className="font-bold">LAUNCH_SCRAPE</h3>
                <p className="text-xs text-green-800">Initiate adaptive multi-layer fetch</p>
              </div>
            </div>
          </div>
          <div className="border border-green-900 bg-black p-4 rounded hover:bg-green-900/20 transition-all cursor-pointer group">
            <div className="flex items-center gap-3">
              <Globe className="group-hover:text-white" />
              <div>
                <h3 className="font-bold">GLOBAL_SWEEP</h3>
                <p className="text-xs text-green-800">Scrape entire internet for intelligence</p>
              </div>
            </div>
          </div>
          <div className="border border-green-900 bg-black p-4 rounded hover:bg-green-900/20 transition-all cursor-pointer group">
            <div className="flex items-center gap-3">
              <Database className="group-hover:text-white" />
              <div>
                <h3 className="font-bold">FS_BROWSER</h3>
                <p className="text-xs text-green-800">Access intelligence asset vault</p>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Footer Nav */}
      <footer className="fixed bottom-0 left-0 w-full p-4 bg-black border-t border-green-900 flex justify-center md:justify-start gap-8 overflow-x-auto whitespace-nowrap">
        <button className="text-green-400 font-bold hover:text-white transition-colors">ROOT:/COMMAND</button>
        <button className="text-green-800 hover:text-green-400 transition-colors">ROOT:/FILES</button>
        <button className="text-green-800 hover:text-green-400 transition-colors">ROOT:/CONFIG</button>
        <button className="text-green-800 hover:text-green-400 transition-colors">ROOT:/WEAPONRY</button>
      </footer>
    </div>
  );
};

export default MainDashboard;
