import React, { useState } from 'react';
import { Layers, FileText, Download, Sparkles, CheckCircle2, Cpu, ChevronDown, FileSpreadsheet, Sliders, Type } from 'lucide-react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'https://exampress-v2-production.up.railway.app';

export default function App() {
  const [bookType, setBookType] = useState('quiz');
  const [formatSize, setFormatSize] = useState('B5');
  const [columnCount, setColumnCount] = useState('2');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [isColOpen, setIsColOpen] = useState(false);
  
  // Advanced Typesetting Control Panel States (Parameters a to g)
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [fontSize, setFontSize] = useState(9.0);
  const [lineSpacing, setLineSpacing] = useState(13.0);
  const [questionGap, setQuestionGap] = useState(6.0);
  const [optionTopGap, setOptionTopGap] = useState(2.0);
  const [columnGapVal, setColumnGapVal] = useState(10.0);
  const [footerBottomMargin, setFooterBottomMargin] = useState(20.0);
  const [optionVerticalGap, setOptionVerticalGap] = useState(1.5);

  // Chapter Heading Toolbar States
  const [showHeadingToolbar, setShowHeadingToolbar] = useState(false);
  const [headerFontSize, setHeaderFontSize] = useState(11.0);
  const [headerBold, setHeaderBold] = useState(true);
  const [headerItalic, setHeaderItalic] = useState(false);
  const [headerAlignment, setHeaderAlignment] = useState(1); // 1 = Center

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
    formData.append('column_count', columnCount);
    
    // Append Advanced Spacing Parameters
    formData.append('font_size', fontSize.toString());
    formData.append('line_spacing', lineSpacing.toString());
    formData.append('question_gap', questionGap.toString());
    formData.append('option_top_gap', optionTopGap.toString());
    formData.append('column_gap_val', columnGapVal.toString());
    formData.append('footer_bottom_margin', footerBottomMargin.toString());
    formData.append('option_vertical_gap', optionVerticalGap.toString());

    // Append Chapter Heading Toolbar Parameters
    formData.append('header_font_size', headerFontSize.toString());
    formData.append('header_bold', headerBold.toString());
    formData.append('header_italic', headerItalic.toString());
    formData.append('header_alignment', headerAlignment.toString());

    if (selectedFile) {
      formData.append('file', selectedFile);
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 90000);

      const response = await fetch(`${BACKEND_URL}/generate-book`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `exampress_${bookType}_${formatSize}_${columnCount}col.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setSuccess(true);
      } else {
        const errorData = await response.json().catch(() => ({}));
        alert(`Failed to generate book: ${errorData.detail || 'Server error'}`);
      }
    } catch (err: any) {
      console.error(err);
      if (err.name === 'AbortError') {
        alert('Backend request timed out. Render/Railway server might be waking up, please try again.');
      } else {
        alert('Error connecting to FastAPI server. Check your connection or Brave shields.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-[#fcfbf9] text-slate-800 flex flex-col items-center justify-center p-6 overflow-x-hidden selection:bg-emerald-500 selection:text-white font-sans">
      <div className="absolute -top-32 -left-32 w-[500px] h-[500px] bg-emerald-200/40 rounded-full blur-[100px] pointer-events-none"></div>
      <div className="absolute -bottom-32 -right-32 w-[500px] h-[500px] bg-stone-200/60 rounded-full blur-[100px] pointer-events-none"></div>

      <div className="relative max-w-xl w-full bg-white/75 backdrop-blur-[35px] border border-emerald-900/10 rounded-[32px] p-8 shadow-[0_20px_50px_rgba(40,50,40,0.06)] my-8">
        <div className="text-center mb-8 flex flex-col items-center">
          <div className="relative mb-3 flex items-center justify-center">
            <div className="absolute w-20 h-20 bg-emerald-400/20 rounded-full blur-xl pointer-events-none animate-pulse"></div>
            <img src="/header-logo.png" alt="Exampur Logo" className="w-16 h-16 object-contain relative z-10" />
          </div>
          <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-200/60 text-emerald-800 text-xs font-semibold px-4 py-1.5 rounded-full uppercase tracking-widest shadow-sm mb-3">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" /> Exampress Engine V2.0 (ReportLab)
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-slate-900">Exampress Studio</h1>
          <p className="text-slate-500 text-sm mt-2 max-w-md mx-auto">
            Next-gen automated typesetting. Press-ready 300 DPI layout compilation with absolute control over spacing.
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

          <div className="grid grid-cols-2 gap-4">
            {/* Page Size Format */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Page Size</label>
              <div className="relative">
                <div 
                  onClick={() => setIsOpen(!isOpen)}
                  className="w-full bg-white/90 border border-slate-200 rounded-2xl px-4 py-3.5 text-slate-700 text-sm flex items-center justify-between cursor-pointer"
                >
                  <span className="font-medium truncate">{formatSize} Size</span>
                  <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180 text-emerald-600' : ''}`} />
                </div>

                <div className={`absolute top-full left-0 right-0 mt-2 bg-white/95 border border-emerald-100 rounded-2xl shadow-xl overflow-hidden z-20 ${isOpen ? 'block' : 'hidden'}`}>
                  <div onClick={() => { setFormatSize('B5'); setIsOpen(false); }} className="px-4 py-3 text-sm cursor-pointer hover:bg-emerald-50">B5 Academic</div>
                  <div onClick={() => { setFormatSize('A4'); setIsOpen(false); }} className="px-4 py-3 text-sm cursor-pointer hover:bg-emerald-50">A4 Standard</div>
                </div>
              </div>
            </div>

            {/* Column Count Selector */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Column Grid</label>
              <div className="relative">
                <div 
                  onClick={() => setIsColOpen(!isColOpen)}
                  className="w-full bg-white/90 border border-slate-200 rounded-2xl px-4 py-3.5 text-slate-700 text-sm flex items-center justify-between cursor-pointer"
                >
                  <span className="font-medium truncate">{columnCount} Columns</span>
                  <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isColOpen ? 'rotate-180 text-emerald-600' : ''}`} />
                </div>

                <div className={`absolute top-full left-0 right-0 mt-2 bg-white/95 border border-emerald-100 rounded-2xl shadow-xl overflow-hidden z-20 ${isColOpen ? 'block' : 'hidden'}`}>
                  <div onClick={() => { setColumnCount('2'); setIsColOpen(false); }} className="px-4 py-3 text-sm cursor-pointer hover:bg-emerald-50">2 Columns (Standard)</div>
                  <div onClick={() => { setColumnCount('3'); setIsColOpen(false); }} className="px-4 py-3 text-sm cursor-pointer hover:bg-emerald-50">3 Columns (Compact)</div>
                </div>
              </div>
            </div>
          </div>

          {/* Chapter Heading Formatting Toolbar */}
          <div className="border border-emerald-900/10 rounded-2xl bg-teal-50/20 p-4">
            <button
              type="button"
              onClick={() => setShowHeadingToolbar(!showHeadingToolbar)}
              className="w-full flex items-center justify-between text-xs font-bold uppercase tracking-wider text-emerald-950 cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <Type className="w-4 h-4 text-emerald-600" /> Chapter Heading Toolbar (Font, Size, Alignment)
              </span>
              <ChevronDown className={`w-4 h-4 transition-transform ${showHeadingToolbar ? 'rotate-180' : ''}`} />
            </button>

            {showHeadingToolbar && (
              <div className="mt-4 space-y-3 pt-3 border-t border-emerald-900/10 text-xs">
                <div>
                  <div className="flex justify-between mb-1 font-medium text-slate-600">
                    <span>Heading Font Size</span>
                    <span className="text-emerald-700 font-bold">{headerFontSize}pt</span>
                  </div>
                  <input type="range" min="9" max="18" step="0.5" value={headerFontSize} onChange={(e) => setHeaderFontSize(Number(e.target.value))} className="w-full accent-emerald-600 cursor-pointer" />
                </div>

                <div className="flex items-center justify-between pt-1">
                  <span className="font-medium text-slate-600">Style Toggles:</span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setHeaderBold(!headerBold)}
                      className={`px-3 py-1 font-bold rounded-lg border text-xs ${headerBold ? 'bg-slate-900 text-white' : 'bg-white text-slate-700'}`}
                    >
                      Bold
                    </button>
                    <button
                      type="button"
                      onClick={() => setHeaderItalic(!headerItalic)}
                      className={`px-3 py-1 italic rounded-lg border text-xs ${headerItalic ? 'bg-slate-900 text-white' : 'bg-white text-slate-700'}`}
                    >
                      Italic
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <span className="font-medium text-slate-600">Alignment:</span>
                  <div className="flex border rounded-lg overflow-hidden bg-white">
                    <button
                      type="button"
                      onClick={() => setHeaderAlignment(0)}
                      className={`px-3 py-1 text-xs ${headerAlignment === 0 ? 'bg-emerald-600 text-white' : 'hover:bg-slate-100 text-slate-700'}`}
                    >
                      Left
                    </button>
                    <button
                      type="button"
                      onClick={() => setHeaderAlignment(1)}
                      className={`px-3 py-1 text-xs ${headerAlignment === 1 ? 'bg-emerald-600 text-white' : 'hover:bg-slate-100 text-slate-700'}`}
                    >
                      Center
                    </button>
                    <button
                      type="button"
                      onClick={() => setHeaderAlignment(2)}
                      className={`px-3 py-1 text-xs ${headerAlignment === 2 ? 'bg-emerald-600 text-white' : 'hover:bg-slate-100 text-slate-700'}`}
                    >
                      Right
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Advanced Spacing Control Panel (Parameters a to g) */}
          <div className="border border-emerald-900/10 rounded-2xl bg-emerald-50/20 p-4">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full flex items-center justify-between text-xs font-bold uppercase tracking-wider text-emerald-950 cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-emerald-600" /> Advanced Spacing Controls (Parameters a-g)
              </span>
              <ChevronDown className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
            </button>

            {showAdvanced && (
              <div className="mt-4 space-y-3 pt-3 border-t border-emerald-900/10 text-xs">
                <div>
                  <div className="flex justify-between mb-1 font-medium text-slate-600">
                    <span>Font Size</span>
                    <span className="text-emerald-700 font-bold">{fontSize}pt</span>
                  </div>
                  <input type="range" min="7" max="14" step="0.5" value={fontSize} onChange={(e) => setFontSize(Number(e.target.value))} className="w-full accent-emerald-600 cursor-pointer" />
                </div>

                <div>
                  <div className="flex justify-between mb-1 font-medium text-slate-600">
                    <span>Line Spacing / Leading (a, b)</span>
                    <span className="text-emerald-700 font-bold">{lineSpacing}pt</span>
                  </div>
                  <input type="range" min="10" max="22" step="0.5" value={lineSpacing} onChange={(e) => setLineSpacing(Number(e.target.value))} className="w-full accent-emerald-600 cursor-pointer" />
                </div>

                <div>
                  <div className="flex justify-between mb-1 font-medium text-slate-600">
                    <span>Question Gap (d)</span>
                    <span className="text-emerald-700 font-bold">{questionGap}px</span>
                  </div>
                  <input type="range" min="2" max="25" step="1" value={questionGap} onChange={(e) => setQuestionGap(Number(e.target.value))} className="w-full accent-emerald-600 cursor-pointer" />
                </div>

                <div>
                  <div className="flex justify-between mb-1 font-medium text-slate-600">
                    <span>Option Top Gap (c)</span>
                    <span className="text-emerald-700 font-bold">{optionTopGap}px</span>
                  </div>
                  <input type="range" min="0" max="15" step="1" value={optionTopGap} onChange={(e) => setOptionTopGap(Number(e.target.value))} className="w-full accent-emerald-600 cursor-pointer" />
                </div>

                <div>
                  <div className="flex justify-between mb-1 font-medium text-slate-600">
                    <span>Column Gutter Gap (e)</span>
                    <span className="text-emerald-700 font-bold">{columnGapVal}px</span>
                  </div>
                  <input type="range" min="5" max="30" step="1" value={columnGapVal} onChange={(e) => setColumnGapVal(Number(e.target.value))} className="w-full accent-emerald-600 cursor-pointer" />
                </div>

                <div>
                  <div className="flex justify-between mb-1 font-medium text-slate-600">
                    <span>Footer Bottom Margin (f)</span>
                    <span className="text-emerald-700 font-bold">{footerBottomMargin}px</span>
                  </div>
                  <input type="range" min="10" max="60" step="5" value={footerBottomMargin} onChange={(e) => setFooterBottomMargin(Number(e.target.value))} className="w-full accent-emerald-600 cursor-pointer" />
                </div>

                <div>
                  <div className="flex justify-between mb-1 font-medium text-slate-600">
                    <span>Option Vertical Gap (g)</span>
                    <span className="text-emerald-700 font-bold">{optionVerticalGap}pt</span>
                  </div>
                  <input type="range" min="0" max="10" step="0.5" value={optionVerticalGap} onChange={(e) => setOptionVerticalGap(Number(e.target.value))} className="w-full accent-emerald-600 cursor-pointer" />
                </div>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Upload Manuscript / Questions (.json, .xlsx, .csv, .docx, .txt, .zip, .rar)</label>
            <label className="border-2 border-dashed border-emerald-300 hover:border-emerald-500 bg-emerald-50/30 rounded-2xl p-4 flex flex-col items-center justify-center cursor-pointer">
              <div className="p-2.5 bg-emerald-100 rounded-xl text-emerald-700 mb-2">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <span className="text-xs font-medium text-slate-700 text-center">
                {selectedFile ? selectedFile.name : "Drop file here or click to browse"}
              </span>
              <input type="file" accept=".json,.xlsx,.xls,.csv,.docx,.txt,.zip,.rar" onChange={handleFileChange} className="hidden" />
            </label>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-4 px-6 bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-600 font-bold rounded-2xl shadow-lg text-white disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer hover:opacity-95 transition-opacity"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span className="text-sm">Compiling ReportLab PDF...</span>
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
            <span>Book compiled successfully via ReportLab! PDF downloaded.</span>
          </div>
        )}
      </div>
      
      <div className="mt-4 mb-2 text-xs text-slate-400 flex items-center gap-1.5 font-medium">
        <Cpu className="w-3.5 h-3.5 text-emerald-600" /> Powered by Exampress V2 ReportLab & FastAPI Engine
      </div>
    </div>
  );
}