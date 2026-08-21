import React, { useState } from 'react';
import client from '../api/client';
import {
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  Building2,
  UserCheck,
  Sparkles,
  ChevronRight,
  ShieldCheck,
  Stethoscope
} from 'lucide-react';

export const DoctorBookingCard = ({ triageData, conversationId, onBookingSuccess }) => {
  const doctor = triageData?.recommended_doctor;
  const [selectedSlot, setSelectedSlot] = useState(doctor?.available_slots?.[0] || null);
  const [bookingLoading, setBookingLoading] = useState(false);
  const [bookingError, setBookingError] = useState('');
  const [confirmedBooking, setConfirmedBooking] = useState(null);

  if (!triageData?.is_finalized || !doctor) return null;

  const topCondition = triageData?.ranked_possibilities?.[0]?.condition || "Clinical Condition";
  const probability = triageData?.ranked_possibilities?.[0]?.probability || "85%";

  const handleBookAppointment = async () => {
    if (!doctor || !selectedSlot) return;
    setBookingLoading(true);
    setBookingError('');
    try {
      // Step 1: Hold provisional draft
      const reserveRes = await client.post('/api/agents/booking/reserve', {
        doctor_id: doctor.doctor_id,
        slot_id: selectedSlot.slot_id,
        conversation_id: conversationId
      });

      // Step 2: Confirm and lock
      const confirmRes = await client.post('/api/agents/booking/confirm', {
        appointment_id: reserveRes.data.appointment_id,
        slot_id: selectedSlot.slot_id
      });

      setConfirmedBooking(confirmRes.data);
      if (onBookingSuccess) onBookingSuccess(confirmRes.data);
    } catch (err) {
      console.error("Booking error:", err);
      setBookingError(err.response?.data?.detail || "Conflict: slot was just claimed. Please choose another time.");
    } finally {
      setBookingLoading(false);
    }
  };

  return (
    <div style={{
      marginTop: '12px',
      borderRadius: '16px',
      background: '#FFFFFF',
      border: '1px solid #E2E8F0',
      boxShadow: '0 4px 16px -2px rgba(11, 90, 84, 0.08), 0 2px 6px -1px rgba(0, 0, 0, 0.04)',
      overflow: 'hidden',
      textAlign: 'left'
    }}>
      {/* Top Banner: Finalized Assessment */}
      <div style={{
        padding: '12px 16px',
        background: 'linear-gradient(135deg, #0B5A54 0%, #14B8A6 100%)',
        color: '#FFFFFF',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '8px',
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Stethoscope size={16} color="#FFFFFF" />
          </div>
          <div>
            <h5 style={{ fontSize: '0.85rem', fontWeight: 800, margin: 0 }}>
              Finalized Clinical Assessment
            </h5>
            <p style={{ fontSize: '0.7rem', color: '#CCFBF1', margin: 0, fontWeight: 600 }}>
              {topCondition} • {probability} Confidence
            </p>
          </div>
        </div>

        <span style={{
          fontSize: '0.65rem',
          fontWeight: 800,
          background: 'rgba(255, 255, 255, 0.25)',
          padding: '3px 8px',
          borderRadius: '9999px',
          textTransform: 'uppercase'
        }}>
          {triageData?.department || 'Specialist'}
        </span>
      </div>

      {/* Body Content */}
      <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {bookingError && (
          <div style={{
            padding: '8px 12px',
            borderRadius: '10px',
            background: '#FFE4E6',
            border: '1px solid #FECDD3',
            color: '#BE123C',
            fontSize: '0.75rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <AlertCircle size={14} />
            <span>{bookingError}</span>
          </div>
        )}

        {confirmedBooking ? (
          <div style={{
            padding: '16px',
            borderRadius: '12px',
            background: '#ECFDF5',
            border: '1px solid #A7F3D0',
            textAlign: 'center'
          }}>
            <CheckCircle2 size={32} color="#059669" style={{ margin: '0 auto 6px auto' }} />
            <h6 style={{ fontSize: '0.9rem', fontWeight: 800, color: '#065F46', margin: '0 0 2px 0' }}>
              Appointment Confirmed!
            </h6>
            <p style={{ fontSize: '0.775rem', color: '#047857', margin: '0 0 8px 0', fontWeight: 500 }}>
              <strong>{confirmedBooking.doctor_name}</strong> • {confirmedBooking.slot_time} ({confirmedBooking.room_no})
            </p>
            <div style={{
              display: 'inline-block',
              padding: '4px 12px',
              borderRadius: '8px',
              background: '#FFFFFF',
              border: '1px solid #6EE7B7',
              fontSize: '0.775rem',
              fontWeight: 800,
              fontFamily: 'monospace',
              color: '#065F46'
            }}>
              Reference: {confirmedBooking.booking_reference}
            </div>
          </div>
        ) : (
          <>
            {/* Recommended Doctor Card */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px',
              borderRadius: '12px',
              background: '#F8FAFC',
              border: '1px solid #E2E8F0'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '12px',
                  background: '#E3F3F1',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#0B5A54',
                  fontWeight: 800
                }}>
                  <UserCheck size={22} />
                </div>
                <div>
                  <h6 style={{ fontSize: '0.875rem', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                    {doctor.name}
                  </h6>
                  <p style={{ fontSize: '0.725rem', color: '#64748B', margin: '1px 0 0 0', fontWeight: 600 }}>
                    {doctor.title} • {doctor.room_no}
                  </p>
                  <p style={{ fontSize: '0.675rem', color: '#0B5A54', margin: '2px 0 0 0', fontWeight: 700 }}>
                    Department of {doctor.department} ({doctor.experience_years} yrs exp)
                  </p>
                </div>
              </div>
            </div>

            {/* Select Slot */}
            <div>
              <span style={{ fontSize: '0.725rem', fontWeight: 700, color: '#0F172A', display: 'block', marginBottom: '6px' }}>
                Choose Preferred Appointment Slot:
              </span>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                {doctor.available_slots?.map((slot) => {
                  const isSelected = selectedSlot?.slot_id === slot.slot_id;
                  return (
                    <button
                      key={slot.slot_id}
                      type="button"
                      onClick={() => setSelectedSlot(slot)}
                      style={{
                        padding: '8px 10px',
                        borderRadius: '10px',
                        border: isSelected ? '2px solid #0B5A54' : '1px solid #E2E8F0',
                        background: isSelected ? '#E3F3F1' : '#F8FAFC',
                        color: isSelected ? '#0B5A54' : '#334155',
                        fontWeight: isSelected ? 800 : 600,
                        fontSize: '0.725rem',
                        cursor: 'pointer',
                        textAlign: 'left',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <Clock size={12} color={isSelected ? '#0B5A54' : '#64748B'} />
                      {slot.slot_time}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Book & Confirm Button */}
            <button
              onClick={handleBookAppointment}
              disabled={bookingLoading || !selectedSlot}
              style={{
                width: '100%',
                padding: '10px 16px',
                borderRadius: '9999px',
                background: 'linear-gradient(135deg, #0B5A54 0%, #14B8A6 100%)',
                color: '#FFFFFF',
                border: 'none',
                fontWeight: 800,
                fontSize: '0.8rem',
                cursor: bookingLoading || !selectedSlot ? 'not-allowed' : 'pointer',
                opacity: bookingLoading || !selectedSlot ? 0.6 : 1,
                boxShadow: '0 4px 12px rgba(11, 90, 84, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                transition: 'all 0.15s ease'
              }}
            >
              <Calendar size={15} />
              <span>{bookingLoading ? "Finalizing Lock..." : `Confirm & Book with ${doctor.name.split(',')[0]}`}</span>
            </button>
          </>
        )}
      </div>
    </div>
  );
};
