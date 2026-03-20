PVObject_=pvModule
  Version=6.43
  Flags=$00100143

  PVObject_Commercial=pvCommercial
    Comment=www.canadiansolar.com
    Flags=$0041
    Manufacturer=Canadian Solar Inc.
    Model=CS6U-330M APP01
    DataSource=Datasheet May2016
    YearBeg=2016
    Width=0.992
    Height=1.960
    Depth=0.040
    Weight=22.40
    NPieces=0
    PriceDate=13/06/16 11:57
    Currency=EUR
    Remarks, Count=7
      Str_1=Created by: KEVHOL (1/16/2017)
      Str_2=Checked-in by: GREEE (1/16/17)
      Str_3
      Str_4=Nameplate Bias: -0.4% (GAIN)
      Str_5=Modeling Error: 0.0% (loss)
      Str_6=Isc StdDev: 1.6%
      Str_7=Voc StdDev: 1.5%
    End of Remarks=Voc StdDev: 1.5%
  End of PVObject pvCommercial

  Technol=mtSiMono
  NCelS=72
  NCelP=1
  NDiode=3
  GRef=1000
  TRef=25.0
  PNom=330.0
  PNomTolLow=0.00
  PNomTolUp=1.50
  Isc=9.310
  Voc=45.90
  Imp=8.800
  Vmp=37.50
  muISC=4.93
  muVocSpec=-143.0
  muPmpReq=-0.420
  RShunt=350
  Rp_0=1400
  Rp_Exp=5.50
  RSerie=0.317
  Gamma=0.971
  muGamma=-0.0006
  VMaxIEC=1000
  VMaxUL=1000
  Absorb=0.90
  ARev=3.200
  BRev=11.290
  RDiode=0.010
  VRevDiode=-0.70
  AirMassRef=1.500
  CellArea=232.3
  LIDLoss=3.00
  SandiaAMCorr=50.000
  RelEffic800=0.09
  RelEffic700=0.23
  RelEffic400=-1.11
  RelEffic200=-2.75

  PVObject_IAM=pvIAM
    Flags=$00
    IAMMode=Default
    B0_IAM=0.05
  End of PVObject pvIAM

  OperPoints, list of=4 tOperPoint
    Point_1=False,200,25.0,-2.75,0.00,0.000,0.000,0.00
    Point_2=False,400,25.0,-1.11,0.00,0.000,0.000,0.00
    Point_3=False,700,25.0,0.23,0.00,0.000,0.000,0.00
    Point_4=False,800,25.0,0.09,0.00,0.000,0.000,0.00
  End of List OperPoints
End of PVObject pvModule
