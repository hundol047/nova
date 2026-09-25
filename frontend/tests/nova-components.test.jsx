import {describe, it, expect} from 'vitest';
import React from 'react';
import {render, screen} from '@testing-library/react';
import {I18nProvider} from '../src/i18n';
import NovaDifferentialPanel from '../src/components/nova/NovaDifferentialPanel';
import NovaCriticalPanel from '../src/components/nova/NovaCriticalPanel';
import NovaNextActionPanel from '../src/components/nova/NovaNextActionPanel';

function wrap(ui, locale = 'en') {
  return render(<I18nProvider initialLocale={locale}>{ui}</I18nProvider>);
}

describe('NovaDifferentialPanel', () => {
  const differential = [
    {
      diagnosis: 'Acute coronary syndrome', display_diagnosis: 'Acute coronary syndrome',
      diagnosis_id: 'acute_coronary_syndrome', rank: 1, confidence_band: 'HIGH', urgency: 'immediate',
      dangerous_if_missed: true, supporting_evidence: ['chest pain'], contradictory_evidence: [],
      missing_discriminative_evidence: ['troponin'], candidate_sources: ['deterministic'],
    },
  ];

  it('shows the canonical diagnosis_id and a LOW/MEDIUM/HIGH band, never a raw %', () => {
    const {container} = wrap(<NovaDifferentialPanel differential={differential} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByText(/acute_coronary_syndrome/)).toBeTruthy();
    expect(screen.getByText(/HIGH/)).toBeTruthy();
    // No percentage sign anywhere in the rendered confidence (R8.4).
    expect(container.textContent).not.toMatch(/\d+\s*%/);
  });

  it('marks dangerous_if_missed items', () => {
    wrap(<NovaDifferentialPanel differential={differential} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByText(/Dangerous if missed/i)).toBeTruthy();
  });
});

describe('NovaCriticalPanel (MUST-NOT-MISS separated from differential)', () => {
  it('renders red flags under the must-not-miss heading', () => {
    wrap(<NovaCriticalPanel redFlags={['Rule out aortic dissection']} />);
    expect(screen.getByText('MUST-NOT-MISS')).toBeTruthy();
    expect(screen.getByText(/aortic dissection/)).toBeTruthy();
  });

  it('shows an empty state when there are no red flags', () => {
    wrap(<NovaCriticalPanel redFlags={[]} />);
    expect(screen.getByText(/No active must-not-miss/i)).toBeTruthy();
  });
});

describe('NovaNextActionPanel', () => {
  it('shows the action type and What/Why', () => {
    const action = {action_type: 'TEST', key: 'troponin', content: 'Order troponin', display_content: 'Order troponin', rationale: 'Rule in/out ACS'};
    wrap(<NovaNextActionPanel action={action} />);
    expect(screen.getByText('TEST')).toBeTruthy();
    expect(screen.getByText('Order troponin')).toBeTruthy();
    expect(screen.getByText('Rule in/out ACS')).toBeTruthy();
  });
});
