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
  Sparkles
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
        // Auto-generate initial reminders
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
    <div className="mt-4 rounded-2xl border border-teal-500/30 bg-gradient-to-b from-slate-900/95 to-slate-950/95 p-4 shadow-xl text-slate-200">
      {/* 4-Agent Pipeline Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
        <div className="flex items-center space-x-2">
          <div className="h-8 w-8 rounded-lg bg-teal-500/20 text-teal-400 flex items-center justify-center font-bold text-xs border border-teal-500/40">
            4-AI
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white flex items-center gap-1.5">
              Multi-Agent Healthcare Guidance System
              <Sparkles className="w-3.5 h-3.5 text-teal-400 animate-pulse" />
            </h4>
            <p className="text-xs text-slate-400">Safe by Design: AI recommends • Human confirms</p>
          </div>
        </div>
      </div>

      {/* 4 Agent Navigation Tabs */}
      <div className="grid grid-cols-4 gap-1 bg-slate-950/60 p-1 rounded-xl border border-slate-800 text-xs font-medium mb-4">
        <button
          onClick={() => setActiveTab('triage')}
          className={`flex items-center justify-center gap-1.5 py-1.5 rounded-lg transition-all ${
            activeTab === 'triage' ? 'bg-teal-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Stethoscope className="w-3.5 h-3.5" />
          <span>1. Triage</span>
        </button>

        <button
          onClick={() => { setActiveTab('booking'); fetchDoctors(department); }}
          className={`flex items-center justify-center gap-1.5 py-1.5 rounded-lg transition-all ${
            activeTab === 'booking' ? 'bg-teal-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Calendar className="w-3.5 h-3.5" />
          <span>2. Booking</span>
        </button>

        <button
          onClick={() => { setActiveTab('soap'); loadSoapReport(); }}
          className={`flex items-center justify-center gap-1.5 py-1.5 rounded-lg transition-all ${
            activeTab === 'soap' ? 'bg-teal-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>3. SOAP Note</span>
        </button>

        <button
          onClick={() => { setActiveTab('care'); loadCareReminders(); }}
          className={`flex items-center justify-center gap-1.5 py-1.5 rounded-lg transition-all ${
            activeTab === 'care' ? 'bg-teal-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Bell className="w-3.5 h-3.5" />
          <span>4. Care</span>
        </button>
      </div>

      {/* TAB 1: TRIAGE AGENT */}
      {activeTab === 'triage' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 rounded-xl bg-teal-950/30 border border-teal-800/40">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-teal-400">Routed Department</span>
              <h5 className="text-base font-bold text-white flex items-center gap-2 mt-0.5">
                <Building2 className="w-4 h-4 text-teal-400" />
                Department of {triageData?.department || 'General Medicine'}
              </h5>
            </div>
            <div className="text-right">
              <span className="text-[11px] text-slate-400">Confidence Gate</span>
              <div className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/30 mt-0.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                {triageData?.confidence_gate || 'ROUTED'}
              </div>
            </div>
          </div>

          <div>
            <h6 className="text-xs font-medium text-slate-300 mb-2">Ranked Possibility Assessment (Preliminary)</h6>
            <div className="space-y-1.5">
              {triageData?.ranked_possibilities?.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-slate-800/60 border border-slate-700/50 text-xs">
                  <span className="text-slate-200">{item.condition}</span>
                  <span className="font-semibold text-teal-400 bg-teal-950/60 px-2 py-0.5 rounded border border-teal-800/40">
                    {item.probability}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              onClick={() => { setActiveTab('booking'); fetchDoctors(department); }}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-medium text-xs shadow-lg shadow-teal-900/30 transition"
            >
              <span>Proceed to Conflict-Free Booking</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* TAB 2: BOOKING AGENT */}
      {activeTab === 'booking' && (
        <div className="space-y-3">
          {bookingError && (
            <div className="p-2.5 rounded-lg bg-rose-950/50 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{bookingError}</span>
            </div>
          )}

          {confirmedAppt ? (
            <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/50 text-center space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
              <h5 className="text-sm font-bold text-white">Appointment Locked & Confirmed!</h5>
              <p className="text-xs text-emerald-200">
                Doctor: <strong>{confirmedAppt.doctor_name}</strong> • {confirmedAppt.slot_time}
              </p>
              <div className="inline-block px-3 py-1 rounded-lg bg-emerald-900/60 border border-emerald-700 text-xs font-mono font-bold text-emerald-300">
                Ref: {confirmedAppt.booking_reference}
              </div>
            </div>
          ) : provisionalAppt ? (
            <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/50 space-y-3">
              <div className="flex items-center gap-2 text-amber-300 text-xs font-semibold">
                <Clock className="w-4 h-4 text-amber-400" />
                <span>Slot Provisionally Held (Requires Confirmation)</span>
              </div>
              <div className="text-xs space-y-1 text-slate-300">
                <p>Doctor: <strong>{provisionalAppt.doctor_name}</strong> ({provisionalAppt.department})</p>
                <p>Location: <strong>{provisionalAppt.room_no}</strong></p>
                <p>Time Slot: <strong>{provisionalAppt.slot_time}</strong></p>
                <p>Reference: <span className="font-mono text-amber-400">{provisionalAppt.booking_reference}</span></p>
              </div>
              <button
                onClick={handleConfirmBooking}
                disabled={bookingLoading}
                className="w-full py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow transition"
              >
                {bookingLoading ? "Finalizing Lock..." : "Confirm & Finalize Appointment Lock"}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Available Doctors in {department}:</label>
                <select
                  value={selectedDoctor?.doctor_id || ''}
                  onChange={(e) => {
                    const doc = doctors.find(d => d.doctor_id === parseInt(e.target.value));
                    setSelectedDoctor(doc);
                    if (doc?.available_slots?.length > 0) setSelectedSlot(doc.available_slots[0]);
                  }}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-teal-500"
                >
                  {doctors.map(d => (
                    <option key={d.doctor_id} value={d.doctor_id}>
                      {d.name} — {d.title} ({d.room_no})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Available Open Slots:</label>
                <div className="grid grid-cols-2 gap-2">
                  {selectedDoctor?.available_slots?.map((slot) => (
                    <button
                      key={slot.slot_id}
                      onClick={() => setSelectedSlot(slot)}
                      className={`p-2 rounded-xl border text-xs font-medium text-left transition ${
                        selectedSlot?.slot_id === slot.slot_id
                          ? 'border-teal-500 bg-teal-950/40 text-teal-300 shadow'
                          : 'border-slate-800 bg-slate-850 text-slate-300 hover:border-slate-700'
                      }`}
                    >
                      <Clock className="w-3.5 h-3.5 text-teal-400 inline-block mr-1.5" />
                      {slot.slot_time}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={handleReserveSlot}
                disabled={bookingLoading || !selectedSlot}
                className="w-full py-2 rounded-xl bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white font-medium text-xs shadow transition"
              >
                {bookingLoading ? "Reserving..." : "Hold Slot & Proceed to Confirmation"}
              </button>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: REPORT AGENT (SOAP NOTE) */}
      {activeTab === 'soap' && (
        <div className="space-y-3">
          {soapLoading ? (
            <div className="py-8 text-center text-xs text-slate-400">Generating structured SOAP clinical draft...</div>
          ) : soapData ? (
            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700 space-y-2">
                <div className="flex items-center justify-between border-b border-slate-700 pb-2">
                  <span className="font-bold text-teal-400">Subjective (S)</span>
                  <span className="text-[10px] text-slate-400">Patient Intake</span>
                </div>
                <p className="text-slate-300 whitespace-pre-line">{soapData.subjective}</p>
              </div>

              <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700 space-y-2">
                <div className="flex items-center justify-between border-b border-slate-700 pb-2">
                  <span className="font-bold text-teal-400">Assessment & Plan (A/P)</span>
                  <span className="text-[10px] text-slate-400">Clinical Formulation</span>
                </div>
                <p className="text-slate-300 whitespace-pre-line">{soapData.assessment}</p>
                <div className="pt-2 border-t border-slate-700/60">
                  <span className="text-[11px] font-semibold text-slate-200">Suggested Preliminary Tests:</span>
                  <ul className="list-disc list-inside text-slate-300 mt-1 space-y-0.5">
                    {soapData.suggested_tests?.map((t, idx) => (
                      <li key={idx}>{t}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {soapApproved ? (
                <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/50 flex items-center gap-2 text-emerald-300">
                  <UserCheck className="w-4 h-4 text-emerald-400" />
                  <span>Approved & Signed by Attending Physician</span>
                </div>
              ) : (
                <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700 space-y-2">
                  <label className="font-medium text-slate-300 block">Doctor Review Checkpoint (Editable Draft):</label>
                  <input
                    type="text"
                    value={doctorNotes}
                    onChange={(e) => setDoctorNotes(e.target.value)}
                    placeholder="Add physician review notes or modifications..."
                    className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-teal-500"
                  />
                  <button
                    onClick={handleApproveSoap}
                    className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-medium text-xs transition"
                  >
                    Physician Review & Approve Note
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="py-6 text-center text-xs text-slate-400">Start symptom chat to generate SOAP note.</div>
          )}
        </div>
      )}

      {/* TAB 4: CARE AGENT */}
      {activeTab === 'care' && (
        <div className="space-y-3">
          <div className="text-xs text-slate-300">
            Post-discharge medication reminders scheduled based on approved treatment protocols:
          </div>

          {remindersLoading ? (
            <div className="py-6 text-center text-xs text-slate-400">Loading care reminders...</div>
          ) : reminders.length > 0 ? (
            <div className="space-y-2">
              {reminders.map((r) => (
                <div key={r.id} className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Pill className="w-4 h-4 text-teal-400" />
                    <div>
                      <h6 className="text-xs font-bold text-white">{r.medication_name} ({r.dosage})</h6>
                      <p className="text-[11px] text-slate-400">{r.frequency} • {r.reminder_time}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleToggleReminder(r.id)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                      r.status === 'active'
                        ? 'bg-emerald-950/60 border border-emerald-700/60 text-emerald-300 hover:bg-emerald-900/60'
                        : 'bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {r.status === 'active' ? 'Active' : 'Paused'}
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-6 text-center text-xs text-slate-400">No active medication reminders.</div>
          )}
        </div>
      )}
    </div>
  );
};
