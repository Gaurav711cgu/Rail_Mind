import React from 'react';
import { Bot, BrainCircuit } from 'lucide-react';

const LLMModeBadge = ({ isAgentic }) => {
  return (
    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
      isAgentic 
        ? 'bg-purple-500/10 text-purple-400 border-purple-500/20 shadow-[0_0_10px_rgba(168,85,247,0.2)]' 
        : 'bg-slate-800 text-slate-400 border-slate-700'
    }`}>
      {isAgentic ? <BrainCircuit className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
      {isAgentic ? 'AGENTIC MODE' : 'LLM FALLBACK'}
    </div>
  );
};

export default LLMModeBadge;
