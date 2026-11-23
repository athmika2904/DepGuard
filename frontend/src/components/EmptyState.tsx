
import React from "react";
import { FileSearch, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface EmptyStateProps {
  title: string;
  description: string;
}

const EmptyState: React.FC<EmptyStateProps> = ({ title, description }) => {
  const navigate = useNavigate();

  return (
    <div className="panel flex flex-col items-center px-6 py-16 text-center">
      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-violet-400/20 bg-violet-400/10">
        <FileSearch size={29} className="text-violet-300" />
      </div>

      <h2 className="text-xl font-bold text-white">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-slate-400">
        {description}
      </p>

      <button
        onClick={() => navigate("/scan")}
        className="button-primary mt-6"
      >
        Run a scan <ArrowRight size={16} />
      </button>
    </div>
  );
};

export default EmptyState;

