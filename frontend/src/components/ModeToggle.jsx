import React from 'react';
import { Play, Activity } from 'lucide-react';

const ModeToggle = ({ isLive, setIsLive, onTriggerLive }) => {
  const handleToggle = () => {
    const nextState = !isLive;
    setIsLive(nextState);
    if (nextState && onTriggerLive) {
      // we just switched to live, maybe trigger immediately or wait for button
    }
  };

  return (
    <div className="flex items-center gap-3 bg-slate-900/50 p-2 rounded-xl border border-slate-800">
      <span className={`text-sm font-medium ${!isLive ? 'text-amber-400' : 'text-slate-500'}`}>
        SCENARIO
      </span>
      <button 
        onClick={handleToggle}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isLive ? 'bg-green-500' : 'bg-slate-700'}`}
      >
        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isLive ? 'translate-x-6' : 'translate-x-1'}`} />
      </button>
      <span className={`text-sm font-medium flex items-center gap-1 ${isLive ? 'text-green-400' : 'text-slate-500'}`}>
        <Activity className="w-4 h-4" /> LIVE
      </span>
      
      {isLive && (
        <button 
          onClick={onTriggerLive}
          className="ml-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors"
        >
          <Play className="w-3 h-3" /> Trigger Agent Run
        </button>
      )}
    </div>
  );
};

export default ModeToggle;
