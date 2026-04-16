clc;
clear;
close all;

%% Parameters
Vdc = 12;              % DC input voltage
f = 50;                % Output frequency (Hz)
T = 1/f;               % Time period
steps = 6;             % 6-step inverter
fs = 50000;            % Simulation sampling frequency
t = 0:1/fs:2*T;        % Simulate 2 cycles

%% Step duration
step_time = T/6;

%% Initialize phase outputs
Va = zeros(size(t));
Vb = zeros(size(t));
Vc = zeros(size(t));

%% Generate 6-step waveform
for k = 1:length(t)
    step = floor(mod(t(k),T)/step_time) + 1;
    
    switch step
        case 1
            A=1; B=0; C=0;
        case 2
            A=1; B=1; C=0;
        case 3
            A=0; B=1; C=0;
        case 4
            A=0; B=1; C=1;
        case 5
            A=0; B=0; C=1;
        case 6
            A=1; B=0; C=1;
    end
    
    Va(k) = (2*A-1)*Vdc/2;
    Vb(k) = (2*B-1)*Vdc/2;
    Vc(k) = (2*C-1)*Vdc/2;
end

%% Line-to-line voltages
Vab = Va - Vb;
Vbc = Vb - Vc;
Vca = Vc - Va;

%% Plot Results

figure;

subplot(4,1,1)
plot(t, Vdc*ones(size(t)),'LineWidth',1.5)
title('Input DC Voltage (12V Battery)')
ylabel('Voltage (V)')
grid on

subplot(4,1,2)
plot(t, Va,'r', t, Vb,'g', t, Vc,'b','LineWidth',1.2)
title('3-Phase Output Phase Voltages (6-Step)')
ylabel('Voltage (V)')
legend('Va','Vb','Vc')
grid on

subplot(4,1,3)
plot(t, Vab,'m','LineWidth',1.2)
title('Line-to-Line Voltage Vab')
ylabel('Voltage (V)')
grid on

subplot(4,1,4)
plot(t, Vbc,'k', t, Vca,'c','LineWidth',1.2)
title('Other Line Voltages Vbc & Vca')
xlabel('Time (seconds)')
ylabel('Voltage (V)')
legend('Vbc','Vca')
grid on