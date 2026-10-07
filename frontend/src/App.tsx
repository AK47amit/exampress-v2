import React, { useState } from 'react';
import { Layers, FileText, Download, Sparkles, CheckCircle2, Cpu, ChevronDown, FileSpreadsheet } from 'lucide-react';

const BACKEND_URL = 'https://exampress-backend.onrender.com';

export default function App() {
  const [bookType, setBookType] = useState('quiz');
  const [formatSize, setFormatSize] = useState('B5');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuccess(false);

    const formData = new FormData();
    formData.append('book_type', bookType);
    formData.append('format_size', formatSize);
    if (selectedFile) {
      formData.append('file', selectedFile);
    }

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
      alert('Error connecting to FastAPI server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-[#fcfbf9] text-slate-800 flex flex-col items-center justify-center p-6 overflow-hidden selection:bg-emerald-500 selection:text-white font-sans">
      <div className="absolute -top-32 -left-32 w-[500px] h-[500px] bg-emerald-200/40 rounded-full blur-[100px] pointer-events-none"></div>
      <div className="absolute -bottom-32 -right-32 w-[500px] h-[500px] bg-stone-200/60 rounded-full blur-[100px] pointer-events-none"></div>

      <div className="relative max-w-xl w-full bg-white/75 backdrop-blur-[35px] border border-emerald-900/10 rounded-[32px] p-8 shadow-[0_20px_50px_rgba(40,50,40,0.06)]">
        <div className="text-center mb-8 flex flex-col items-center">
          <div className="relative mb-3 flex items-center justify-center">
            <div className="absolute w-20 h-20 bg-emerald-400/20 rounded-full blur-xl pointer-events-none animate-pulse"></div>
            <img src="/header-logo.png" alt="Exampur Logo" className="w-16 h-16 object-contain relative z-10" />
          </div>
          <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-200/60 text-emerald-800 text-xs font-semibold px-4 py-1.5 rounded-full uppercase tracking-widest shadow-sm mb-3">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" /> Exampress Engine V2.0
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-slate-900">Exampress Studio</h1>
          <p className="text-slate-500 text-sm mt-2 max-w-md mx-auto">
            Next-gen automated typesetting. Replace manual InDesign workflows with press-ready 300 DPI layout compilation in seconds.
          </p>
        </div>

        <form onSubmit={handleGenerate} className="space-y-6">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Select Layout Structure</label>
            <div className="grid grid-cols-2 gap-4">
              <div 
                onClick={() => setBookType('quiz')}
                className={`cursor-pointer rounded-2xl p-4 transition-all duration-300 flex flex-col justify-between border ${
                  bookType === 'quiz' ? 'bg-emerald-50 border-emerald-500/50 shadow-md text-emerald-950' : 'bg-white/50 border-slate-200 text-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className={`p-2 rounded-xl ${bookType === 'quiz' ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-500'}`}>
                    <Layers className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-200/50 text-emerald-900">Grid</span>
                </div>
                <div>
                  <div className="font-bold text-sm">Mock Quiz</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Multi-column blocks</div>
                </div>
              </div>

              <div 
                onClick={() => setBookType('notes')}
                className={`cursor-pointer rounded-2xl p-4 transition-all duration-300 flex flex-col justify-between border ${
                  bookType === 'notes' ? 'bg-emerald-50 border-emerald-500/50 shadow-md text-emerald-950' : 'bg-white/50 border-slate-200 text-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className={`p-2 rounded-xl ${bookType === 'notes' ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-500'}`}>
                    <FileText className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-200/50 text-emerald-900">Doc</span>
                </div>
                <div>
                  <div className="font-bold text-sm">Theory Notes</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Structured callouts</div>
                </div>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Page Size Format</label>
            <div className="relative">
              <div 
                onClick={() => setIsOpen(!isOpen)}
                className="w-full bg-white/90 border border-slate-200 rounded-2xl px-4 py-3.5 text-slate-700 text-sm flex items-center justify-between cursor-pointer"
              >
                <span className="font-medium">
                  {formatSize === 'B5' ? 'B5 Academic Size (Competitive Books)' : 'A4 Standard Format (Comprehensive Guides)'}
                </span>
                <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180 text-emerald-600' : ''}`} />
              </div>

              <div className={`absolute top-full left-0 right-0 mt-2 bg-white/95 border border-emerald-100 rounded-2xl shadow-xl overflow-hidden z-20 ${isOpen ? 'block' : 'hidden'}`}>
                <div 
                  onClick={() => { setFormatSize('B5'); setIsOpen(false); }}
                  className="px-4 py-3.5 text-sm cursor-pointer hover:bg-emerald-50"
                >
                  B5 Academic Size (Competitive Books)
                </div>
                <div 
                  onClick={() => { setFormatSize('A4'); setIsOpen(false); }}
                  className="px-4 py-3.5 text-sm cursor-pointer hover:bg-emerald-50"
                >
                  A4 Standard Format (Comprehensive Guides)
                </div>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Upload Manuscript / Questions (.json, .xlsx, .csv, .docx, .txt, .zip, .rar)</label>
            <label className="border-2 border-dashed border-emerald-300 hover:border-emerald-500 bg-emerald-50/30 rounded-2xl p-4 flex flex-col items-center justify-center cursor-pointer">
              <div className="p-2.5 bg-emerald-100 rounded-xl text-emerald-700 mb-2">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <span className="text-xs font-medium text-slate-700 text-center">
                {selectedFile ? selectedFile.name : "Drop file here or click to browse (JSON, Excel, Word, CSV, ZIP, RAR)"}
              </span>
              <input type="file" accept=".json,.xlsx,.xls,.csv,.docx,.txt,.zip,.rar" onChange={handleFileChange} className="hidden" />
            </label>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-4 px-6 bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-600 font-bold rounded-2xl shadow-lg text-white disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span className="text-sm">Compiling Typeset...</span>
              </>
            ) : (
              <>
                <Download className="w-5 h-5" />
                <span className="text-sm">Generate Press-Ready PDF</span>
              </>
            )}
          </button>
        </form>

        {success && (
          <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-3 text-emerald-800 text-sm">
            <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-600" />
            <span>Book compiled successfully! PDF downloaded to your machine.</span>
          </div>
        )}
      </div>
      
      <div className="absolute bottom-4 text-xs text-slate-400 flex items-center gap-1.5 font-medium">
        <Cpu className="w-3.5 h-3.5 text-emerald-600" /> Powered by Exampress V2 Core & FastAPI Engine
      </div>
    </div>
  );
}