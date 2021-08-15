function tripGPS2Ahmed(gpsdata, output_trips_path)
% ��GPS�켣������(CarID, X, Y, Time,Dir,Speed,IsBusy)ת��ΪAhmed map construction����
% ���Դ����trip_#.txt�����ļ�
%

if ~exist(output_trips_path, 'dir')
    mkdir(output_trips_path);
end

GPSTIME_IND = 4;
gpsdata(:,GPSTIME_IND) = round(( gpsdata(:,GPSTIME_IND) - min(gpsdata(:,GPSTIME_IND)) )*(24*60*60));
carId = gpsdata(:,1);
Id = unique( carId );

count = -1;
min_nodes_num = 5; % ÿһ���켣���ٰ����ĵ���Ŀ


for i=1:length(Id)
    d = gpsdata(carId==Id(i), [2,3,4]);
    if size(d,1) >= min_nodes_num
        count = count + 1;
        fid = fopen(fullfile(output_trips_path, ['trip_', num2str(count), '.txt']), 'w');
        for j=1:size(d,1)
            fprintf(fid, '%.6f %.6f %.1f\r\n', d(j,1), d(j,2), d(j,3));
        end
        fclose(fid);
    end
end

end % 


