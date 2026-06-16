"use client";

interface MultiSelectOption {
  value: string;
  label: string;
  description?: string;
}

interface MultiSelectProps {
  options: MultiSelectOption[];
  values: string[];
  onChange: (values: string[]) => void;
}

export function MultiSelect({ options, values, onChange }: MultiSelectProps) {
  const toggle = (val: string) => {
    if (values.includes(val)) {
      onChange(values.filter((v) => v !== val));
    } else {
      onChange([...values, val]);
    }
  };

  return (
    <div className="space-y-2">
      {options.map((opt) => {
        const selected = values.includes(opt.value);
        return (
          <button
            key={opt.value}
            type="button"
            className={`w-full text-left p-3 rounded-lg border transition-colors ${
              selected
                ? "border-blue-600 bg-blue-600/10"
                : "border-gray-800 bg-gray-800/50 hover:border-gray-700"
            }`}
            onClick={() => toggle(opt.value)}
          >
            <div className="flex items-center gap-2">
              <div
                className={`w-4 h-4 rounded border-2 flex items-center justify-center ${
                  selected ? "border-blue-600 bg-blue-600" : "border-gray-600"
                }`}
              >
                {selected && (
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              <span className="text-sm font-medium">{opt.label}</span>
            </div>
            {opt.description && (
              <div className="text-xs text-gray-500 mt-1 ml-6">{opt.description}</div>
            )}
          </button>
        );
      })}
    </div>
  );
}
