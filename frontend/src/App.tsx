import React, { useState } from 'react';
import { Layers, FileText, Download, Sparkles, CheckCircle2, Cpu, ChevronDown } from 'lucide-react';

// Define backend base URL dynamically (supports local dev & Vercel production)
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export default function App() {
  const [bookType, setBookType] = useState('quiz');
  const [formatSize, setFormatSize] = useState('B5');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuccess(false);

    const formData = new FormData();
    formData.append('book_type', bookType);
    formData.append('format_size', formatSize);

    try {
      const response = await fetch(`${BACKEND_URL}/generate-book`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        // Fixed formatSize camelCase here
        a.download = `exampress_${bookType}_${formatSize}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setSuccess(true);
      } else {
        const errorData = await response.json().catch(() => ({}));
        alert(`Failed to generate book: ${errorData.detail || 'Server error'}`);
      }
    } catch (err) {
      console.error(err);
      alert('Error connecting to FastAPI server. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-[#fcfbf9] text-slate-800 flex flex-col items-center justify-center p-6 overflow-hidden selection:bg-emerald-500 selection:text-white font-sans">
      
      {/* Soft Creamy & Pista Ambient Glow Background */}
      <div className="absolute -top-32 -left-32 w-[500px] h-[500px] bg-emerald-200/40 rounded-full blur-[100px] pointer-events-none transition-all duration-700"></div>
      <div className="absolute -bottom-32 -right-32 w-[500px] h-[500px] bg-stone-200/60 rounded-full blur-[100px] pointer-events-none"></div>

      {/* Creamy Glass Card with Pista Green Accents */}
      <div className="relative max-w-xl w-full bg-white/75 backdrop-blur-[35px] border border-emerald-900/10 rounded-[32px] p-8 shadow-[0_20px_50px_rgba(40,50,40,0.06)] ring-1 ring-black/[0.03] transition-all duration-500">
        
        {/* Header Logo & Badge */}
        <div className="text-center mb-8 flex flex-col items-center">
          <div className="relative mb-3 flex items-center justify-center">
            <div className="absolute w-20 h-20 bg-emerald-400/20 rounded-full blur-xl pointer-events-none animate-pulse"></div>
            <img 
              src="/header-logo.png" 
              alt="Exampur Logo" 
              className="w-16 h-16 object-contain relative z-10 drop-shadow-md hover:scale-105 transition-transform duration-300" 
            />
          </div>
          <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-200/60 text-emerald-800 text-xs font-semibold px-4 py-1.5 rounded-full uppercase tracking-widest shadow-sm mb-3">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" /> Exampress Engine V2.0
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-slate-900">
            Exampress Studio
          </h1>
          <p className="text-slate-500 text-sm mt-2 max-w-md mx-auto">
            Next-gen automated typesetting. Replace manual InDesign workflows with press-ready 300 DPI layout compilation in seconds.
          </p>
        </div>

        {/* Form Controls */}
        <form onSubmit={handleGenerate} className="space-y-6">
          
          {/* Layout Structure Picker */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Select Layout Structure</label>
            <div className="grid grid-cols-2 gap-4">
              
              <div 
                onClick={() => setBookType('quiz')}
                className={`cursor-pointer rounded-2xl p-4 transition-all duration-300 flex flex-col justify-between border transform hover:-translate-y-1 hover:shadow-lg ${
                  bookType === 'quiz' 
                    ? 'bg-gradient-to-br from-emerald-50 to-emerald-100/60 border-emerald-500/50 shadow-[0_6px_22px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/30 text-emerald-950' 
                    : 'bg-white/50 border-slate-200/80 hover:border-emerald-400 hover:bg-white text-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className={`p-2 rounded-xl transition-colors ${bookType === 'quiz' ? 'bg-emerald-500 text-white shadow-md shadow-emerald-500/20' : 'bg-slate-100 text-slate-500'}`}>
                    <Layers className="w-5 h-5" />
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${bookType === 'quiz' ? 'bg-emerald-200/50 border-emerald-300 text-emerald-900' : 'bg-slate-100 border-slate-200 text-slate-600'}`}>Grid</span>
                </div>
                <div>
                  <div className="font-bold text-sm">Mock Quiz</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Multi-column blocks</div>
                </div>
              </div>

              <div 
                onClick={() => setBookType('notes')}
                className={`cursor-pointer rounded-2xl p-4 transition-all duration-300 flex flex-col justify-between border transform hover:-translate-y-1 hover:shadow-lg ${
                  bookType === 'notes' 
                    ? 'bg-gradient-to-br from-emerald-50 to-emerald-100/60 border-emerald-500/50 shadow-[0_6px_22px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/30 text-emerald-950' 
                    : 'bg-white/50 border-slate-200/80 hover:border-emerald-400 hover:bg-white text-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className={`p-2 rounded-xl transition-colors ${bookType === 'notes' ? 'bg-emerald-500 text-white shadow-md shadow-emerald-500/20' : 'bg-slate-100 text-slate-500'}`}>
                    <FileText className="w-5 h-5" />
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${bookType === 'notes' ? 'bg-emerald-200/50 border-emerald-300 text-emerald-900' : 'bg-slate-100 border-slate-200 text-slate-600'}`}>Doc</span>
                </div>
                <div>
                  <div className="font-bold text-sm">Theory Notes</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Structured callouts</div>
                </div>
              </div>

            </div>
          </div>

          {/* Custom Dropdown */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Page Size Format</label>
            <div className="relative">
              
              <div 
                onClick={() => setIsOpen(!isOpen)}
                className="w-full bg-white/90 border border-slate-200/90 rounded-2xl px-4 py-3.5 text-slate-700 text-sm flex items-center justify-between cursor-pointer transition-all duration-300 hover:border-emerald-500 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0 transform"
              >
                <span className="font-medium">
                  {formatSize === 'B5' ? 'B5 Academic Size (Competitive Books)' : 'A4 Standard Format (Comprehensive Guides)'}
                </span>
                <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform duration-300 ${isOpen ? 'rotate-180 text-emerald-600' : ''}`} />
              </div>

              {/* Dropdown Menu */}
              <div className={`absolute top-full left-0 right-0 mt-2 bg-white/95 backdrop-blur-xl border border-emerald-100 rounded-2xl shadow-xl overflow-hidden z-20 transition-all duration-300 origin-top ${
                isOpen ? 'opacity-100 scale-y-100 translate-y-0' : 'opacity-0 scale-y-95 -translate-y-2 pointer-events-none'
              }`}>
                <div 
                  onClick={() => { setFormatSize('B5'); setIsOpen(false); }}
                  className={`px-4 py-3.5 text-sm cursor-pointer transition-all relative group ${
                    formatSize === 'B5' ? 'bg-emerald-50 text-emerald-950 font-semibold' : 'text-slate-600 hover:bg-emerald-50/40 hover:text-emerald-900'
                  }`}
                >
                  <span className="relative z-10 transition-transform duration-200 group-hover:translate-x-1 inline-block">B5 Academic Size (Competitive Books)</span>
                  <div className="absolute bottom-0 left-4 right-4 h-[2px] bg-emerald-500 scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left"></div>
                </div>
                
                <div 
                  onClick={() => { setFormatSize('A4'); setIsOpen(false); }}
                  className={`px-4 py-3.5 text-sm cursor-pointer transition-all relative group ${
                    formatSize === 'A4' ? 'bg-emerald-50 text-emerald-950 font-semibold' : 'text-slate-600 hover:bg-emerald-50/40 hover:text-emerald-900'
                  }`}
                >
                  <span className="relative z-10 transition-transform duration-200 group-hover:translate-x-1 inline-block">A4 Standard Format (Comprehensive Guides)</span>
                  <div className="absolute bottom-0 left-4 right-4 h-[2px] bg-emerald-500 scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left"></div>
                </div>
              </div>

            </div>
          </div>

          {/* Action Button */}
          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-4 px-6 bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-600 font-bold rounded-2xl shadow-[0_10px_25px_rgba(16,185,129,0.3)] hover:shadow-[0_15px_30px_rgba(16,185,129,0.45)] hover:scale-[1.01] active:scale-[0.99] transition-all duration-200 flex items-center justify-center gap-2 text-white disabled:opacity-50"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span className="text-sm tracking-wide">Compiling 300 DPI Typeset...</span>
              </>
            ) : (
              <>
                <Download className="w-5 h-5" />
                <span className="text-sm tracking-wide">Generate Press-Ready PDF</span>
              </>
            )}
          </button>
        </form>

        {/* Success Feedback Card */}
        {success && (
          <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-3 text-emerald-800 text-sm animate-fade-in">
            <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-600" />
            <span>Book compiled successfully! PDF downloaded to your machine.</span>
          </div>
        )}

      </div>
      
      {/* Footer Branding */}
      <div className="absolute bottom-4 text-xs text-slate-400 flex items-center gap-1.5 font-medium">
        <Cpu className="w-3.5 h-3.5 text-emerald-600" /> Powered by Exampress V2 Core & FastAPI Engine
      </div>
    </div>
  );
}