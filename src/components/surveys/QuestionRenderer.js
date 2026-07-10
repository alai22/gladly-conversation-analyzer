import React from 'react';

function RatingInput({ value, onChange, labels, disabled }) {
  const nums = [1, 2, 3, 4, 5];
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {nums.map((n) => (
          <button
            key={n}
            type="button"
            disabled={disabled}
            onClick={() => onChange(n)}
            className={`w-11 h-11 rounded-full border-2 font-semibold transition-colors ${
              value === n
                ? 'bg-halo-yellow border-halo-yellow text-halo-black'
                : 'border-gray-300 text-gray-700 hover:border-halo-yellow'
            } disabled:opacity-50`}
          >
            {n}
          </button>
        ))}
      </div>
      {(labels?.min || labels?.max) && (
        <div className="flex justify-between text-xs text-gray-500 mt-2">
          <span>{labels.min}</span>
          <span>{labels.max}</span>
        </div>
      )}
    </div>
  );
}

function ChoiceInput({ question, value, onChange, disabled, multi }) {
  const selected = multi ? (Array.isArray(value) ? value : []) : value;

  const toggle = (opt) => {
    if (multi) {
      const arr = Array.isArray(selected) ? [...selected] : [];
      if (arr.includes(opt)) onChange(arr.filter((o) => o !== opt));
      else onChange([...arr, opt]);
    } else {
      onChange(opt);
    }
  };

  return (
    <div className="space-y-2">
      {question.options.map((opt) => {
        const isSelected = multi ? selected.includes(opt) : selected === opt;
        return (
          <label
            key={opt}
            className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
              isSelected
                ? 'border-halo-yellow bg-halo-yellow-light'
                : 'border-gray-200 hover:border-gray-300'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <input
              type={multi ? 'checkbox' : 'radio'}
              name={question.id}
              checked={isSelected}
              disabled={disabled}
              onChange={() => toggle(opt)}
              className="mt-1 accent-halo-yellow"
            />
            <span className="text-sm text-halo-black">{opt}</span>
          </label>
        );
      })}
    </div>
  );
}

export default function QuestionRenderer({ question, value, onChange, disabled = false }) {
  if (!question) return null;

  return (
    <div className="mb-6">
      <label className="block text-base font-medium text-halo-black mb-1">
        {question.text}
        {question.required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {question.help_text && (
        <p className="text-sm text-gray-500 mb-3">{question.help_text}</p>
      )}

      {question.type === 'single_choice' && (
        <ChoiceInput question={question} value={value} onChange={onChange} disabled={disabled} />
      )}

      {question.type === 'multi_select' && (
        <ChoiceInput question={question} value={value} onChange={onChange} disabled={disabled} multi />
      )}

      {question.type === 'rating' && (
        <RatingInput
          value={value}
          onChange={onChange}
          labels={question.labels}
          disabled={disabled}
        />
      )}

      {question.type === 'rating_with_text' && (
        <div className="space-y-4">
          <RatingInput
            value={value?.rating}
            onChange={(n) => onChange({ ...value, rating: n })}
            labels={question.labels}
            disabled={disabled}
          />
          <div>
            <label className="block text-sm text-gray-600 mb-1">
              {question.text_prompt || 'Additional comments'}
            </label>
            <textarea
              value={value?.text || ''}
              onChange={(e) => onChange({ ...value, text: e.target.value })}
              disabled={disabled}
              rows={3}
              placeholder={question.placeholder || ''}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-halo-yellow focus:border-halo-yellow text-sm"
            />
          </div>
        </div>
      )}

      {question.type === 'short_text' && (
        <input
          type="text"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={question.placeholder || ''}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-halo-yellow focus:border-halo-yellow text-sm"
        />
      )}

      {question.type === 'long_text' && (
        <textarea
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          rows={4}
          placeholder={question.placeholder || ''}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-halo-yellow focus:border-halo-yellow text-sm"
        />
      )}
    </div>
  );
}
