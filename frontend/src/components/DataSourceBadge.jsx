import { Database, Zap } from 'lucide-react';

const DataSourceBadge = ({ source }) => {
  const isLive = source === 'NTES' || source === 'RAILWAYAPI';
  
  return (
    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
      isLive 
        ? 'bg-green-500/10 text-green-400 border-green-500/20' 
        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
    }`}>
      {isLive ? <Zap className="w-3.5 h-3.5" /> : <Database className="w-3.5 h-3.5" />}
      {isLive ? 'LIVE DATA' : 'SCENARIO DATA'}
    </div>
  );
};

export default DataSourceBadge;
