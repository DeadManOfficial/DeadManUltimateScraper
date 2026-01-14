import React, { useState } from 'react';
import { Search, FileText, HardDrive, FileJson, Clock, Filter } from 'lucide-react';

const FileBrowser: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');

  const files = [
    { name: "nasa_audit_trail.jsonl", size: "8.5 KB", date: "2026-01-14", type: "log" },
    { name: "central_scraper.py", size: "7.6 KB", date: "2026-01-14", type: "code" },
    { name: "mission_briefing.json", size: "45 KB", date: "2026-01-14", type: "json" },
    { name: "synthid_bypass_report.md", size: "12 KB", date: "2026-01-14", type: "report" }
  ];

  return (
    <div className="min-h-screen bg-black text-green-500 p-4 md:p-8 font-mono">
      <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <HardDrive className="text-white" />
          ASSET_VAULT
        </h1>
        
        {/* Search Bar */}
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-green-900" size={18} />
          <input 
            type="text"
            placeholder="FILTER_INTEL..."
            className="w-full bg-black border border-green-900 rounded p-2 pl-10 focus:outline-none focus:border-green-400 text-white"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </header>

      {/* File List Table */}
      <div className="border border-green-900 rounded-lg overflow-hidden bg-green-900/5">
        <div className="hidden md:grid grid-cols-4 gap-4 p-4 border-b border-green-900 text-xs text-green-800 uppercase tracking-widest bg-black">
          <div>ASSET_NAME</div>
          <div>SIZE</div>
          <div>TIMESTAMP</div>
          <div>TYPE</div>
        </div>

        <div className="divide-y divide-green-900">
          {files.map((file, i) => (
            <div key={i} className="grid grid-cols-1 md:grid-cols-4 gap-2 md:gap-4 p-4 hover:bg-green-900/20 transition-all cursor-pointer group">
              <div className="flex items-center gap-3">
                <FileJson size={18} className="group-hover:text-white" />
                <span className="text-white font-bold truncate">{file.name}</span>
              </div>
              <div className="text-xs md:text-sm text-green-700 md:text-green-500 flex items-center gap-2">
                <span className="md:hidden">SIZE:</span> {file.size}
              </div>
              <div className="text-xs md:text-sm text-green-700 md:text-green-500 flex items-center gap-2">
                <span className="md:hidden">DATE:</span> {file.date}
              </div>
              <div className="flex items-center">
                <span className="px-2 py-1 text-[10px] border border-green-900 rounded text-green-900 uppercase">
                  {file.type}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pagination Footer */}
      <div className="mt-6 flex justify-between items-center text-xs text-green-900 uppercase">
        <div>DISPLAYING: {files.length} ASSETS</div>
        <div className="flex gap-4">
          <button className="hover:text-white disabled:opacity-50">PREV_BLOCK</button>
          <button className="text-green-400">01</button>
          <button className="hover:text-white disabled:opacity-50">NEXT_BLOCK</button>
        </div>
      </div>
    </div>
  );
};

export default FileBrowser;
