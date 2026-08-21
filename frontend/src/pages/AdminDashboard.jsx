import React, { useState, useEffect } from 'react';
import client from '../api/client';
import {
  MessageSquare,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ThumbsUp,
  Ticket as TicketIcon,
  RefreshCw,
  TrendingUp
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis
} from 'recharts';

export const AdminDashboard = () => {
  const [metrics, setMetrics] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updatingTicketId, setUpdatingTicketId] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [mRes, tRes] = await Promise.all([
        client.get('/metrics/summary'),
        client.get('/tickets')
      ]);
      setMetrics(mRes.data);
      setTickets(tRes.data);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleStatusChange = async (ticketId, newStatus) => {
    try {
      setUpdatingTicketId(ticketId);
      const res = await client.patch(`/tickets/${ticketId}/status`, { status: newStatus });
      setTickets((prev) => prev.map((t) => t.id === ticketId ? res.data : t));
      // Refresh summary metrics
      const mRes = await client.get('/metrics/summary');
      setMetrics(mRes.data);
    } catch (err) {
      console.error("Failed to update ticket status:", err);
      alert("Failed to update ticket status");
    } finally {
      setUpdatingTicketId(null);
    }
  };

  if (loading && !metrics) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 'calc(100vh - 80px)', color: '#94a3b8' }}>
        <RefreshCw size={24} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
        <span style={{ marginLeft: '10px' }}>Loading Command Center Metrics...</span>
      </div>
    );
  }

  // Chart data preparation
  const pieData = metrics ? [
    { name: 'Resolved', value: metrics.resolved_conversations, color: '#10b981' },
    { name: 'Escalated', value: metrics.escalated_conversations, color: '#f43f5e' },
    { name: 'Open Active', value: metrics.open_conversations, color: '#6366f1' }
  ] : [];

  const getPriorityStyle = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'urgent':
        return { bg: 'rgba(244, 63, 94, 0.2)', color: '#fb7185', border: 'rgba(244, 63, 94, 0.4)' };
      case 'high':
        return { bg: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', border: 'rgba(245, 158, 11, 0.4)' };
      default:
        return { bg: 'rgba(99, 102, 241, 0.2)', color: '#a5b4fc', border: 'rgba(99, 102, 241, 0.4)' };
    }
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '32px 24px' }}>
      {/* Top Title & Refresh */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '28px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc' }}>
            Metrics & Operations Dashboard
          </h1>
          <p style={{ fontSize: '0.875rem', color: '#94a3b8', marginTop: '4px' }}>
            Real-time analytics, resolution rates, and human escalation queue management
          </p>
        </div>
        <button onClick={fetchData} className="btn-secondary">
          <RefreshCw size={16} /> Refresh Metrics
        </button>
      </div>

      {/* METRICS CARDS GRID */}
      {metrics && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '16px',
          marginBottom: '32px'
        }}>
          {/* Card 1 */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '10px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Conversations</span>
              <MessageSquare size={18} color="#6366f1" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#ffffff' }}>{metrics.total_conversations}</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>{metrics.total_messages} total messages</div>
          </div>

          {/* Card 2 */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '10px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Resolution Rate</span>
              <CheckCircle2 size={18} color="#10b981" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#34d399' }}>{metrics.resolution_rate}%</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>{metrics.resolved_conversations} closed out</div>
          </div>

          {/* Card 3 */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '10px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Escalation Rate</span>
              <AlertTriangle size={18} color="#f43f5e" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fb7185' }}>{metrics.escalation_rate}%</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>{metrics.open_tickets_count} pending tickets</div>
          </div>

          {/* Card 4 */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '10px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Avg Latency</span>
              <Clock size={18} color="#f59e0b" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fbbf24' }}>{metrics.avg_response_time_ms}<span style={{ fontSize: '0.9rem', fontWeight: 500 }}>ms</span></div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Per bot response</div>
          </div>

          {/* Card 5 */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '10px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>CSAT Rating</span>
              <ThumbsUp size={18} color="#38bdf8" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#38bdf8' }}>{metrics.satisfaction_score}%</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Positive feedback ratio</div>
          </div>
        </div>
      )}

      {/* CHARTS SECTION */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px', marginBottom: '36px' }}>
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={18} color="#6366f1" /> Conversation Status Breakdown
          </h3>
          <div style={{ width: '100%', height: '240px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#1e293b', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                />
                <Legend formatter={(value) => <span style={{ color: '#cbd5e1', fontSize: '0.85rem' }}>{value}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TicketIcon size={18} color="#06b6d4" /> Escalation Queue Snapshot
          </h3>
          <div style={{ width: '100%', height: '240px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[
                { name: 'Open', count: tickets.filter(t => t.status === 'open').length, fill: '#f43f5e' },
                { name: 'In Progress', count: tickets.filter(t => t.status === 'in_progress').length, fill: '#f59e0b' },
                { name: 'Closed', count: tickets.filter(t => t.status === 'closed').length, fill: '#10b981' }
              ]}>
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#1e293b', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {
                    [
                      { fill: '#f43f5e' },
                      { fill: '#f59e0b' },
                      { fill: '#10b981' }
                    ].map((entry, index) => (
                      <Cell key={`bar-${index}`} fill={entry.fill} />
                    ))
                  }
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ESCALATION TICKETS QUEUE TABLE */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={20} color="#f43f5e" /> Live Human Escalation Queue ({tickets.length})
          </h3>
        </div>

        {tickets.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#64748b', fontSize: '0.9rem' }}>
            No tickets escalated yet! The Copilot is handling inquiries automatically.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Ticket ID</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Customer</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Intent</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Priority</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Escalation Reason</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => {
                  const pStyle = getPriorityStyle(t.priority);
                  return (
                    <tr key={t.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', transition: 'background 0.15s' }}>
                      <td style={{ padding: '14px 16px', fontWeight: 700, color: '#cbd5e1' }}>#{t.id}</td>
                      <td style={{ padding: '14px 16px', color: '#e2e8f0' }}>{t.user_email}</td>
                      <td style={{ padding: '14px 16px', textTransform: 'capitalize', color: '#94a3b8' }}>{t.intent}</td>
                      <td style={{ padding: '14px 16px' }}>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '6px',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          background: pStyle.bg,
                          color: pStyle.color,
                          border: `1px solid ${pStyle.border}`
                        }}>
                          {t.priority}
                        </span>
                      </td>
                      <td style={{ padding: '14px 16px', color: '#cbd5e1', maxWidth: '300px' }}>{t.reason}</td>
                      <td style={{ padding: '14px 16px' }}>
                        <select
                          value={t.status}
                          disabled={updatingTicketId === t.id}
                          onChange={(e) => handleStatusChange(t.id, e.target.value)}
                          className="glass-input"
                          style={{
                            padding: '6px 10px',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            color: t.status === 'closed' ? '#34d399' : (t.status === 'in_progress' ? '#fbbf24' : '#fb7185'),
                            background: 'rgba(15, 23, 42, 0.9)'
                          }}
                        >
                          <option value="open">🔴 Open</option>
                          <option value="in_progress">🟡 In Progress</option>
                          <option value="closed">🟢 Closed</option>
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
