import React, { useState, useEffect } from 'react';
import client from '../api/client';
import {
  Stethoscope,
  Calendar,
  FileText,
  Bell,
  CheckCircle2,
  AlertCircle,
  Clock,
  UserCheck,
  ChevronRight,
  ShieldCheck,
  Building2,
  Pill,
  Sparkles,
  User
} from 'lucide-react';

export const AgentWorkflowCard = ({ triageData, conversationId, onBookingSuccess }) => {
  const [activeTab, setActiveTab] = useState('triage'); // triage | booking | soap | care
  const [department, setDepartment] = useState(triageData?.department || 'General Medicine');
  const [doctors, setDoctors] = useState([]);
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [provisionalAppt, setProvisionalAppt] = useState(null);
  const [confirmedAppt, setConfirmedAppt] = useState(null);
  const [bookingLoading, setBookingLoading] = useState(false);
  const [bookingError, setBookingError] = useState('');

  // Agent 3: SOAP State
  const [soapData, setSoapData] = useState(null);
  const [soapLoading, setSoapLoading] = useState(false);
  const [doctorNotes, setDoctorNotes] = useState('');
  const [soapApproved, setSoapApproved] = useState(false);

  // Agent 4: Care Reminders State
  const [reminders, setReminders] = useState([]);
  const [remindersLoading, setRemindersLoading] = useState(false);

  useEffect(() => {
    if (triageData?.department) {
      setDepartment(triageData.department);
      fetchDoctors(triageData.department);
    }
  }, [triageData]);

  const fetchDoctors = async (dept) => {
    try {
      setBookingLoading(true);
      const res = await client.get(`/api/agents/booking/slots?department=${encodeURIComponent(dept)}`);
      setDoctors(res.data);
      if (res.data.length > 0) {
        setSelectedDoctor(res.data[0]);
        if (res.data[0].available_slots?.length > 0) {
          setSelectedSlot(res.data[0].available_slots[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load doctor slots:", err);
    } finally {
      setBookingLoading(false);
    }
  };

  const handleReserveSlot = async () => {
    if (!selectedDoctor || !selectedSlot) return;
    setBookingLoading(true);
    setBookingError('');
    try {
      const res = await client.post('/api/agents/booking/reserve', {
        doctor_id: selectedDoctor.doctor_id,
        slot_id: selectedSlot.slot_id,
        conversation_id: conversationId
      });
      setProvisionalAppt(res.data);
    } catch (err) {
      setBookingError(err.response?.data?.detail || "Failed to hold slot. It may have just been booked.");
    } finally {
      setBookingLoading(false);
    }
  };

  const handleConfirmBooking = async () => {
    if (!provisionalAppt) return;
    setBookingLoading(true);
    setBookingError('');
    try {
      const res = await client.post('/api/agents/booking/confirm', {
        appointment_id: provisionalAppt.appointment_id,
        slot_id: selectedSlot.slot_id
      });
      setConfirmedAppt(res.data);
      if (onBookingSuccess) onBookingSuccess(res.data);
    } catch (err) {
      setBookingError(err.response?.data?.detail || "Conflict error: Slot lock failed.");
    } finally {
      setBookingLoading(false);
    }
  };

  const loadSoapReport = async () => {
    if (!conversationId) return;
    setSoapLoading(true);
    try {
      const res = await client.get(`/api/agents/reports/soap/${conversationId}`);
      setSoapData(res.data);
      setSoapApproved(res.data.doctor_reviewed);
    } catch (err) {
      console.error("Failed to load SOAP report:", err);
    } finally {
      setSoapLoading(false);
    }
  };

  const handleApproveSoap = async () => {
    if (!soapData) return;
    try {
      await client.post(`/api/agents/reports/soap/${soapData.id}/approve`, {
        doctor_notes: doctorNotes || "Approved after physician review."
      });
      setSoapApproved(true);
    } catch (err) {
      console.error("Failed to approve SOAP note:", err);
    }
  };

  const loadCareReminders = async () => {
    setRemindersLoading(true);
    try {
      const res = await client.get('/api/agents/care/reminders');
      if (res.data.length === 0) {
        const genRes = await client.post('/api/agents/care/reminders/generate', {});
        setReminders(genRes.data);
      } else {
        setReminders(res.data);
      }
    } catch (err) {
      console.error("Failed to load care reminders:", err);
    } finally {
      setRemindersLoading(false);
    }
  };

  const handleToggleReminder = async (id) => {
    try {
      const res = await client.post(`/api/agents/care/reminders/${id}/toggle`);
      setReminders(prev => prev.map(r => r.id === id ? { ...r, status: res.data.status } : r));
    } catch (err) {
      console.error("Failed to toggle reminder:", err);
    }
  };

  return (
    <div style={{
      marginTop: '16px',
      borderRadius: '20px',
      background: '#FFFFFF',
      border: '1px solid #E2E8F0',
      boxShadow: '0 4px 20px -2px rgba(11, 90, 84, 0.08), 0 2px 6px -1px rgba(0, 0, 0, 0.04)',
      overflow: 'hidden',
      textAlign: 'left'
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 18px',
        background: 'linear-gradient(135deg, #0B5A54 0%, #14B8A6 100%)',
        color: '#FFFFFF',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '10px',
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '0.75rem'
          }}>
            4-AI
          </div>
          <div>
            <h4 style={{ fontSize: '0.875rem', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
              Multi-Agent Clinical Pipeline
              <Sparkles size={14} color="#A7F3D0" />
            </h4>
            <p style={{ fontSize: '0.7rem', color: '#CCFBF1', margin: 0, fontWeight: 500 }}>
              AI Recommends • Human Checkpoint Finalizes
            </p>
          </div>
        </div>

        <span style={{
          fontSize: '0.65rem',
          fontWeight: 700,
          background: 'rgba(255, 255, 255, 0.25)',
          padding: '4px 8px',
          borderRadius: '9999px',
          textTransform: 'uppercase',
          letterSpacing: '0.05em'
        }}>
          Live Connected
        </span>
      </div>

      {/* 4 Agent Navigation Tabs */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        background: '#F8FAFC',
        padding: '6px',
        borderBottom: '1px solid #E2E8F0',
        gap: '4px'
      }}>
        {[
          { id: 'triage', label: '1. Triage', icon: Stethoscope },
          { id: 'booking', label: '2. Booking', icon: Calendar, action: () => fetchDoctors(department) },
          { id: 'soap', label: '3. SOAP Note', icon: FileText, action: loadSoapReport },
          { id: 'care', label: '4. Care', icon: Bell, action: loadCareReminders }
        ].map((tab) => {
          const Icon = tab.icon;
          const isSelected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                if (tab.action) tab.action();
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '5px',
                padding: '8px 4px',
                borderRadius: '12px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: isSelected ? 800 : 600,
                color: isSelected ? '#FFFFFF' : '#64748B',
                background: isSelected ? '#0B5A54' : 'transparent',
                boxShadow: isSelected ? '0 2px 8px rgba(11, 90, 84, 0.25)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Body */}
      <div style={{ padding: '16px' }}>
        {/* TAB 1: TRIAGE AGENT */}
        {activeTab === 'triage' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 14px',
              borderRadius: '14px',
              background: '#E3F3F1',
              border: '1px solid rgba(11, 90, 84, 0.15)'
            }}>
              <div>
                <span style={{ fontSize: '0.65rem', fontWeight: 800, color: '#0B5A54', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Recommended Department
                </span>
                <h5 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0F172A', margin: '2px 0 0 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Building2 size={16} color="#0B5A54" />
                  Department of {triageData?.department || 'General Medicine'}
                </h5>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.65rem', color: '#64748B', display: 'block', fontWeight: 600 }}>Confidence Gate</span>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.7rem',
                  fontWeight: 800,
                  color: '#0B5A54',
                  background: '#FFFFFF',
                  padding: '3px 8px',
                  borderRadius: '9999px',
                  border: '1px solid rgba(11, 90, 84, 0.2)'
                }}>
                  <ShieldCheck size={12} color="#0B5A54" />
                  {triageData?.confidence_gate || 'ROUTED'}
                </span>
              </div>
            </div>

            <div>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0F172A', display: 'block', marginBottom: '8px' }}>
                Ranked Possibility Assessment (Preliminary, Not Diagnosis)
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {triageData?.ranked_possibilities?.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 12px',
                      borderRadius: '12px',
                      background: '#F8FAFC',
                      border: '1px solid #E2E8F0',
                      fontSize: '0.8rem'
                    }}
                  >
                    <span style={{ color: '#1E293B', fontWeight: 600 }}>{item.condition}</span>
                    <span style={{
                      fontWeight: 800,
                      color: '#0B5A54',
                      background: '#E3F3F1',
                      padding: '2px 8px',
                      borderRadius: '9999px',
                      fontSize: '0.75rem'
                    }}>
                      {item.probability}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '6px' }}>
              <button
                onClick={() => {
                  setActiveTab('booking');
                  fetchDoctors(department);
                }}
                className="btn-primary"
                style={{ fontSize: '0.8rem', padding: '9px 16px' }}
              >
                <span>Proceed to Conflict-Free Booking</span>
                <ChevronRight size={15} />
              </button>
            </div>
          </div>
        )}

        {/* TAB 2: BOOKING AGENT */}
        {activeTab === 'booking' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {bookingError && (
              <div style={{
                padding: '10px 12px',
                borderRadius: '12px',
                background: '#FFE4E6',
                border: '1px solid #FECDD3',
                color: '#BE123C',
                fontSize: '0.75rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <AlertCircle size={16} />
                <span>{bookingError}</span>
              </div>
            )}

            {confirmedAppt ? (
              <div style={{
                padding: '20px',
                borderRadius: '16px',
                background: '#ECFDF5',
                border: '1px solid #A7F3D0',
                textAlign: 'center'
              }}>
                <CheckCircle2 size={36} color="#059669" style={{ margin: '0 auto 8px auto' }} />
                <h5 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#065F46', margin: '0 0 4px 0' }}>
                  Appointment Locked & Confirmed!
                </h5>
                <p style={{ fontSize: '0.8rem', color: '#047857', margin: '0 0 10px 0', fontWeight: 500 }}>
                  Doctor: <strong>{confirmedAppt.doctor_name}</strong> • {confirmedAppt.slot_time}
                </p>
                <div style={{
                  display: 'inline-block',
                  padding: '6px 14px',
                  borderRadius: '10px',
                  background: '#FFFFFF',
                  border: '1px solid #6EE7B7',
                  fontSize: '0.8rem',
                  fontWeight: 800,
                  fontFamily: 'monospace',
                  color: '#065F46'
                }}>
                  Ref: {confirmedAppt.booking_reference}
                </div>
              </div>
            ) : provisionalAppt ? (
              <div style={{
                padding: '16px',
                borderRadius: '14px',
                background: '#FFFBEB',
                border: '1px solid #FDE68A',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#B45309', fontSize: '0.8rem', fontWeight: 700 }}>
                  <Clock size={16} />
                  <span>Slot Provisionally Held (Requires Confirmation)</span>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#78350F', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  <p style={{ margin: 0 }}>Doctor: <strong>{provisionalAppt.doctor_name}</strong> ({provisionalAppt.department})</p>
                  <p style={{ margin: 0 }}>Location: <strong>{provisionalAppt.room_no}</strong></p>
                  <p style={{ margin: 0 }}>Time: <strong>{provisionalAppt.slot_time}</strong></p>
                  <p style={{ margin: 0 }}>Reference: <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{provisionalAppt.booking_reference}</span></p>
                </div>
                <button
                  onClick={handleConfirmBooking}
                  disabled={bookingLoading}
                  className="btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.85rem' }}
                >
                  {bookingLoading ? "Finalizing Lock..." : "Confirm & Finalize Appointment Lock"}
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0F172A', display: 'block', marginBottom: '6px' }}>
                    Available Specialists in {department}:
                  </label>
                  <select
                    value={selectedDoctor?.doctor_id || ''}
                    onChange={(e) => {
                      const doc = doctors.find(d => d.doctor_id === parseInt(e.target.value));
                      setSelectedDoctor(doc);
                      if (doc?.available_slots?.length > 0) setSelectedSlot(doc.available_slots[0]);
                    }}
                    className="input-carepulse"
                  >
                    {doctors.map(d => (
                      <option key={d.doctor_id} value={d.doctor_id}>
                        {d.name} — {d.title} ({d.room_no})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0F172A', display: 'block', marginBottom: '6px' }}>
                    Live Available Slots:
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    {selectedDoctor?.available_slots?.map((slot) => {
                      const isSelected = selectedSlot?.slot_id === slot.slot_id;
                      return (
                        <button
                          key={slot.slot_id}
                          onClick={() => setSelectedSlot(slot)}
                          style={{
                            padding: '10px 12px',
                            borderRadius: '12px',
                            border: isSelected ? '2px solid #0B5A54' : '1px solid #E2E8F0',
                            background: isSelected ? '#E3F3F1' : '#F8FAFC',
                            color: isSelected ? '#0B5A54' : '#1E293B',
                            fontWeight: isSelected ? 800 : 600,
                            fontSize: '0.75rem',
                            cursor: 'pointer',
                            textAlign: 'left',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            transition: 'all 0.15s ease'
                          }}
                        >
                          <Clock size={14} color={isSelected ? '#0B5A54' : '#64748B'} />
                          {slot.slot_time}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <button
                  onClick={handleReserveSlot}
                  disabled={bookingLoading || !selectedSlot}
                  className="btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.85rem' }}
                >
                  {bookingLoading ? "Reserving..." : "Hold Slot & Proceed to Confirmation"}
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: REPORT AGENT (SOAP NOTE) */}
        {activeTab === 'soap' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.8rem' }}>
            {soapLoading ? (
              <div style={{ padding: '24px', textAlign: 'center', color: '#64748B' }}>
                Synthesizing structured SOAP clinical draft note...
              </div>
            ) : soapData ? (
              <>
                <div style={{ padding: '12px', borderRadius: '12px', background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 800, color: '#0B5A54' }}>Subjective (S)</span>
                    <span style={{ fontSize: '0.7rem', color: '#64748B' }}>Patient Intake</span>
                  </div>
                  <p style={{ color: '#334155', margin: 0, whiteSpace: 'pre-line', lineHeight: 1.5 }}>
                    {soapData.subjective}
                  </p>
                </div>

                <div style={{ padding: '12px', borderRadius: '12px', background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 800, color: '#0B5A54' }}>Assessment & Plan (A/P)</span>
                    <span style={{ fontSize: '0.7rem', color: '#64748B' }}>Clinical Formulation</span>
                  </div>
                  <p style={{ color: '#334155', margin: '0 0 8px 0', whiteSpace: 'pre-line', lineHeight: 1.5 }}>
                    {soapData.assessment}
                  </p>
                  <div style={{ borderTop: '1px solid #E2E8F0', paddingTop: '6px' }}>
                    <span style={{ fontWeight: 700, color: '#0F172A', display: 'block', marginBottom: '4px' }}>
                      Suggested Preliminary Diagnostic Tests:
                    </span>
                    <ul style={{ margin: 0, paddingLeft: '18px', color: '#475569' }}>
                      {soapData.suggested_tests?.map((t, idx) => (
                        <li key={idx}>{t}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                {soapApproved ? (
                  <div style={{
                    padding: '10px 14px',
                    borderRadius: '12px',
                    background: '#ECFDF5',
                    border: '1px solid #A7F3D0',
                    color: '#065F46',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontWeight: 700
                  }}>
                    <UserCheck size={18} color="#059669" />
                    <span>Approved & Signed by Attending Physician</span>
                  </div>
                ) : (
                  <div style={{
                    padding: '12px',
                    borderRadius: '12px',
                    background: '#F1F5F9',
                    border: '1px solid #CBD5E1',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}>
                    <label style={{ fontWeight: 700, color: '#0F172A' }}>Doctor Review Checkpoint (Editable Draft):</label>
                    <input
                      type="text"
                      value={doctorNotes}
                      onChange={(e) => setDoctorNotes(e.target.value)}
                      placeholder="Add physician review notes or modifications..."
                      className="input-carepulse"
                      style={{ background: '#FFFFFF' }}
                    />
                    <button
                      onClick={handleApproveSoap}
                      className="btn-primary"
                      style={{ fontSize: '0.8rem', padding: '8px 14px' }}
                    >
                      Physician Review & Approve Note
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div style={{ padding: '20px', textAlign: 'center', color: '#64748B' }}>
                Start a symptom intake chat to generate a SOAP note.
              </div>
            )}
          </div>
        )}

        {/* TAB 4: CARE AGENT */}
        {activeTab === 'care' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <p style={{ fontSize: '0.75rem', color: '#64748B', margin: 0 }}>
              Post-discharge medication reminders scheduled based on approved treatment protocols:
            </p>

            {remindersLoading ? (
              <div style={{ padding: '20px', textAlign: 'center', color: '#64748B', fontSize: '0.8rem' }}>
                Loading care reminders...
              </div>
            ) : reminders.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {reminders.map((r) => (
                  <div
                    key={r.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 14px',
                      borderRadius: '14px',
                      background: '#F8FAFC',
                      border: '1px solid #E2E8F0'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '10px',
                        background: '#E3F3F1',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#0B5A54'
                      }}>
                        <Pill size={16} />
                      </div>
                      <div>
                        <h6 style={{ fontSize: '0.825rem', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                          {r.medication_name} ({r.dosage})
                        </h6>
                        <p style={{ fontSize: '0.7rem', color: '#64748B', margin: '2px 0 0 0', fontWeight: 500 }}>
                          {r.frequency} • {r.reminder_time}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleToggleReminder(r.id)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '9999px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        border: 'none',
                        cursor: 'pointer',
                        background: r.status === 'active' ? '#D1FAE5' : '#F1F5F9',
                        color: r.status === 'active' ? '#047857' : '#64748B',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      {r.status === 'active' ? 'Active' : 'Paused'}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '20px', textAlign: 'center', color: '#64748B', fontSize: '0.8rem' }}>
                No active medication reminders.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
